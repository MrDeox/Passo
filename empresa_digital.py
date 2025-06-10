# -*- coding: utf-8 -*-
"""Simulador de uma empresa digital impulsionada por Modelos de Linguagem (LLMs).

Este módulo define a estrutura central para simular uma empresa onde agentes,
representados como entidades de software, tomam decisões e interagem com base
em prompts processados por LLMs através da API OpenRouter.
Ele gerencia o estado da empresa, incluindo agentes, locais, finanças e
o fluxo de eventos e decisões.
"""

import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import logging
import random  # Adicionado para seleção aleatória de agentes
import time  # Adicionado para o backoff exponencial
import requests  # Adicionado para chamadas HTTP
# import json # Já importado acima
# import logging # Já importado acima

# Imports do ciclo_criativo para persistência do histórico de ideias
# e de core_types para a definição de Ideia.
from .core_types import Ideia
from ciclo_criativo import salvar_historico_ideias, carregar_historico_ideias

# A funcao para buscar a API key deve vir de openrouter_utils para evitar
# dependencias circulares com o modulo `api` utilizado nos testes e no backend.
from openrouter_utils import obter_api_key

logger = logging.getLogger(__name__)

# Permite ativar o modo Vida Infinita via variavel de ambiente
MODO_VIDA_INFINITA: bool = os.environ.get("MODO_VIDA_INFINITA", "0") == "1"

def definir_modo_vida_infinita(ativo: bool) -> None:
    global MODO_VIDA_INFINITA
    MODO_VIDA_INFINITA = ativo
    registrar_evento(f"Modo Vida Infinita {'ativado' if ativo else 'desativado'}.")
    logger.info(f"Modo Vida Infinita {'ativado' if ativo else 'desativado'}.")

# Configurable delay for OpenRouter API calls
# Purpose: To control the request rate, avoid hitting rate limits, or for debugging.
OPENROUTER_CALL_DELAY_SECONDS: float = 1.0

# Maximum number of agents to process with LLM calls per cycle
# Purpose: To manage API costs and processing time during simulation.
MAX_LLM_AGENTS_PER_CYCLE: int = 5

# ---------------------------- Lucro da empresa ----------------------------
# Saldo acumulado da empresa ao longo da simulação. Cada ciclo soma receitas e
# subtrai custos fixos. O histórico é usado pelo dashboard para gerar gráficos.
saldo: float = 0.0
historico_saldo: List[float] = []

# Lista global de tarefas pendentes que podem ser atribuídas a novos agentes
tarefas_pendentes: List[str] = []

# Dicionários globais para armazenar os agentes e os locais cadastrados.
agentes: Dict[str, "Agente"] = {}
locais: Dict[str, "Local"] = {}

historico_eventos: List[str] = []


def registrar_evento(msg: str) -> None:
    historico_eventos.append(msg)
    logging.info("EVENTO: %s", msg)


@dataclass
class Local:
    """Representa um local na empresa.

    Attributes:
        nome: Nome do local (chave no dicionário global).
        descricao: Breve descrição do local.
        inventario: Lista de recursos ou ferramentas disponíveis.
        agentes_presentes: Lista de agentes atualmente neste local.
    """

    nome: str
    descricao: str
    inventario: List[str] = field(default_factory=list)
    agentes_presentes: List["Agente"] = field(default_factory=list)

    def adicionar_agente(self, agente: "Agente") -> None:
        """Adiciona um agente à lista de presentes."""
        if agente not in self.agentes_presentes:
            self.agentes_presentes.append(agente)

    def remover_agente(self, agente: "Agente") -> None:
        """Remove um agente da lista de presentes se estiver nela."""
        if agente in self.agentes_presentes:
            self.agentes_presentes.remove(agente)


@dataclass
class Agente:
    """Representa um agente (funcionário ou bot) na empresa digital.

    As decisões do agente são conduzidas por um Modelo de Linguagem (LLM)
    especificado em `modelo_llm`, que é usado para chamadas via OpenRouter.
    """

    nome: str
    funcao: str
    modelo_llm: str  # Modelo de LLM da OpenRouter (ex: "anthropic/claude-3-haiku", "openai/gpt-4-turbo")
    local_atual: Optional[Local] = None
    historico_acoes: List[str] = field(default_factory=list)
    historico_interacoes: List[str] = field(default_factory=list)
    historico_locais: List[str] = field(default_factory=list)
    objetivo_atual: str = ""
    feedback_ceo: str = ""
    estado_emocional: int = 0

    def mover_para(self, novo_local: Local) -> None:
        """Move o agente para um novo local, atualizando todas as referências."""
        if self.local_atual is not None:
            self.local_atual.remover_agente(self)
        novo_local.adicionar_agente(self)
        self.local_atual = novo_local
        # Registra o local visitado mantendo apenas os dois últimos
        self.historico_locais.append(novo_local.nome)
        if len(self.historico_locais) > 2:
            self.historico_locais = self.historico_locais[-2:]

    def registrar_acao(self, descricao: str, sucesso: bool) -> None:
        """Registra uma ação executada e ajusta o estado emocional."""
        self.historico_acoes.append(descricao)
        if len(self.historico_acoes) > 3:
            self.historico_acoes = self.historico_acoes[-3:]

        # Ajusta o estado emocional em função do resultado da ação.
        self.estado_emocional += 1 if sucesso else -1
        # Limita o valor entre -5 e 5 para evitar exageros.
        self.estado_emocional = max(-5, min(5, self.estado_emocional))


# ---------------------------------------------------------------------------
# Lógica autônoma de inicialização e escolha de modelos
# ---------------------------------------------------------------------------

from openrouter_utils import buscar_modelos_gratis, escolher_modelo_llm


def selecionar_modelo(funcao: str, objetivo: str = "") -> Tuple[str, str]:
    """Escolhe dinamicamente o modelo de linguagem para um agente."""

    # Algumas funções possuem escolha fixa por heurística simples para acelerar
    # os testes e evitar dependência de chamadas externas.
    heuristicas = {"Dev": "deepseek-chat", "CEO": "phi-4:free"}
    if funcao in heuristicas:
        modelo = heuristicas[funcao]
        raciocinio = "heuristica"
    else:
        modelos = buscar_modelos_gratis()
        modelo, raciocinio = escolher_modelo_llm(funcao, objetivo, modelos)

    logging.info(
        "Modelo %s escolhido para funcao %s - %s", modelo, funcao, raciocinio
    )
    return modelo, raciocinio


def _decidir_salas_iniciais() -> List[Tuple[str, str, List[str]]]:
    """Simula via LLM quais salas criar inicialmente."""

    return [
        ("Planejamento", "Sala para estratégias iniciais", ["quadro", "internet"]),
        (
            "Laboratorio IA",
            "Espaço para experimentos de IA",
            ["computadores", "gpu"],
        ),
    ]


def _decidir_agentes_iniciais() -> List[Tuple[str, str, str, str, str]]:
    """Define quais agentes iniciarão a empresa."""

    configuracoes = [
        ("Clara", "CEO", "Planejamento", "Definir metas iniciais"),
        ("Rafael", "Ideacao", "Laboratorio IA", "Gerar ideias de produtos"),
        ("Marta", "Validador", "Planejamento", "Avaliar viabilidade"),
    ]
    agentes_cfg = []
    for nome, funcao, sala, objetivo in configuracoes:
        modelo, motivo = selecionar_modelo(funcao, objetivo)
        logging.info(
            "Modelo %s escolhido para %s (%s) - %s",
            modelo,
            nome,
            funcao,
            motivo,
        )
        agentes_cfg.append((nome, funcao, modelo, sala, objetivo))
    return agentes_cfg


def inicializar_automaticamente() -> None:
    """Cria toda a estrutura inicial sem inputs humanos."""

    if agentes or locais:
        logging.info("Empresa já inicializada")
        return

    logging.info("Inicialização autônoma da empresa")
    for nome, desc, inv in _decidir_salas_iniciais():
        criar_local(nome, desc, inv)
        logging.info("Sala criada: %s - %s", nome, desc)

    for nome, funcao, modelo, sala, objetivo in _decidir_agentes_iniciais():
        criar_agente(nome, funcao, modelo, sala, objetivo)
        logging.info(
            "Agente criado: %s em %s como %s", nome, sala, funcao
        )

    tarefas_pendentes.append("Planejar estratégia de lançamento")
    logging.info("Tarefa inicial registrada: Planejar estratégia de lançamento")


# ---------------------------------------------------------------------------
# Funções de manipulação de agentes e locais
# ---------------------------------------------------------------------------


def criar_agente(
    nome: str,
    funcao: str,
    modelo_llm: str,
    local: str,
    objetivo: str = ""
) -> Agente:
    """Cria um novo agente e adiciona aos registros.

    Args:
        nome: Nome do agente.
        funcao: Cargo ou função do agente.
        modelo_llm: Modelo de LLM utilizado (ex.: "gpt-3.5-turbo").
        local: Nome do local onde o agente iniciará.
        objetivo: Objetivo inicial associado ao agente.

    Returns:
        O objeto ``Agente`` criado.
    """
    local_obj = locais.get(local)
    if local_obj is None:
        raise ValueError(f"Local '{local}' não encontrado.")

    agente = Agente(
        nome=nome,
        funcao=funcao,
        modelo_llm=modelo_llm,
        local_atual=local_obj,
        objetivo_atual=objetivo,
    )
    agentes[nome] = agente
    local_obj.adicionar_agente(agente)
    agente.historico_locais.append(local_obj.nome)
    return agente


def criar_local(
    nome: str, descricao: str, inventario: Optional[List[str]] = None
) -> Local:
    """Cria um novo local e adiciona aos registros."""
    local = Local(nome=nome, descricao=descricao, inventario=inventario or [])
    locais[nome] = local
    return local


def mover_agente(nome_agente: str, nome_novo_local: str) -> None:
    """Move um agente para outro local.

    Atualiza o ``local_atual`` do agente e as listas de ``agentes_presentes``
    tanto do local de origem quanto do novo local.
    """
    agente = agentes.get(nome_agente)
    if agente is None:
        raise ValueError(f"Agente '{nome_agente}' não encontrado.")

    novo_local = locais.get(nome_novo_local)
    if novo_local is None:
        raise ValueError(f"Local '{nome_novo_local}' não encontrado.")

    agente.mover_para(novo_local)


def adicionar_tarefa(tarefa: str) -> None:
    """Registra uma nova tarefa pendente."""
    tarefas_pendentes.append(tarefa)


def salvar_dados(arquivo_agentes: str, arquivo_locais: str, arquivo_historico_ideias: str = "historico_ideias.json") -> None:
    """Salva os dicionários globais de agentes, locais e o histórico de ideias em arquivos JSON.

    Somente informações necessárias para reconstrução dos objetos são
    persistidas (nome do local em que cada agente está, por exemplo).
    """

    # Serializa agentes registrando apenas dados essenciais e o nome do local
    dados_agentes = {
        nome: {
            "nome": ag.nome,
            "funcao": ag.funcao,
            "modelo_llm": ag.modelo_llm,
            "local_atual": ag.local_atual.nome if ag.local_atual else None,
            "historico_acoes": ag.historico_acoes,
            "historico_interacoes": ag.historico_interacoes,
            "historico_locais": ag.historico_locais,
            "objetivo_atual": ag.objetivo_atual,
            "feedback_ceo": ag.feedback_ceo,
            "estado_emocional": ag.estado_emocional,
        }
        for nome, ag in agentes.items()
    }
    with open(arquivo_agentes, "w", encoding="utf-8") as f:
        json.dump(dados_agentes, f, ensure_ascii=False, indent=2)

    # Serializa locais ignorando a lista de agentes presentes, pois ela será
    # reconstruída ao carregar os agentes
    dados_locais = {
        nome: {
            "nome": loc.nome,
            "descricao": loc.descricao,
            "inventario": loc.inventario,
        }
        for nome, loc in locais.items()
    }
    with open(arquivo_locais, "w", encoding="utf-8") as f:
        json.dump(dados_locais, f, ensure_ascii=False, indent=2)

    # Salvar histórico de ideias
    salvar_historico_ideias(arquivo_historico_ideias)


def carregar_dados(arquivo_agentes: str, arquivo_locais: str, arquivo_historico_ideias: str = "historico_ideias.json") -> None:
    """Carrega arquivos JSON recriando os dicionários de agentes, locais e o histórico de ideias."""

    global agentes, locais
    agentes = {}
    locais = {}

    # Carrega primeiro os locais, pois os agentes dependem deles
    with open(arquivo_locais, "r", encoding="utf-8") as f:
        dados_locais = json.load(f)
    for info in dados_locais.values():
        criar_local(info["nome"], info["descricao"], info.get("inventario"))

    # Agora recria os agentes e os adiciona aos locais correspondentes
    with open(arquivo_agentes, "r", encoding="utf-8") as f:
        dados_agentes = json.load(f)
    for info in dados_agentes.values():
        # Garantir que o local_atual seja tratado se None ou vazio
        local_atual_nome = info.get("local_atual")
        if not local_atual_nome or local_atual_nome not in locais:
            # Fallback para um local padrão ou logar um aviso e pular/tratar o agente
            # Por enquanto, se o local não existir, pode causar erro em criar_agente
            # ou o agente pode ficar sem local. criar_agente já lida com local não encontrado.
            # Se local_atual_nome for None, criar_agente pode precisar de um default.
            # A lógica original de criar_agente espera um nome de local válido.
            # Se o local salvo for inválido, o agente não será movido corretamente.
            # Vamos garantir que `criar_agente` receba uma string, mesmo que vazia se não houver local.
            # A função `criar_agente` já levanta ValueError se o local não for encontrado.
            # Se o local for None/vazio, pode ser um agente que ainda não foi atribuído a um local.
            # A função `criar_agente` precisa de um nome de local. Se for None, precisa de um default.
            # A assinatura de criar_agente é: nome, funcao, modelo_llm, local, objetivo
            # O `local` é o nome do local.
            # Se `info.get("local_atual")` for None, passamos uma string vazia ou um local padrão se existir.
            # No entanto, a lógica de `criar_agente` espera um local que exista.
            # Melhorar isso pode ser um refactoring. Por ora, passamos o que foi salvo.
            # Se for None, `criar_agente` vai falhar se não encontrar `locais[None]`.
            # Portanto, é importante que `local_atual` em `dados_agentes` seja um nome de local válido ou
            # que `criar_agente` e `agente.mover_para` lidem com `None`.
            # A estrutura de `Agente` permite `local_atual: Optional[Local]`.
            # `criar_agente` atribui `local_obj` a `agente.local_atual`. Se `local` (nome) não existe, falha.
            # Se `info.get("local_atual")` for `None`, isso é um problema para `locais.get(None)`.
            # Vamos assumir que se `local_atual` é `None` no JSON, o agente não está em nenhum local específico
            # ou está em um local "default" ou "limbo".
            # Para simplificar, se `local_atual` for None no JSON, o agente é criado sem local inicial
            # e depois tentamos movê-lo. Mas `criar_agente` exige um local.
            # Solução: se local_atual for None, não podemos criar o agente da forma usual.
            # Isso indica um estado salvo potencialmente inconsistente ou um agente "desligado".
            # Por ora, vamos pular agentes com local inválido no carregamento, com um log.
            if not local_atual_nome or local_atual_nome not in locais:
                logger.warning(f"Agente '{info['nome']}' tem local_atual '{local_atual_nome}' inválido ou não encontrado nos locais carregados. Este agente pode não ser carregado corretamente ou ser pulado.")
                # Opção 1: Pular o agente
                # continue
                # Opção 2: Tentar criar com um local padrão (se existir) ou levantar erro.
                # Por ora, a chamada a criar_agente abaixo vai falhar se local_atual_nome for inválido.
                # Uma melhoria seria criar o agente e não atribuir local se inválido.
                # Mas a assinatura de criar_agente exige um local.
                # Vamos deixar como está e `criar_agente` levantará o erro se o local for ruim.
                pass # Deixa a lógica original de criar_agente lidar com isso.

        # Corrigindo a passagem do local para criar_agente:
        # Se o local_atual não estiver definido no JSON, ou for None,
        # precisamos de um nome de local válido para criar_agente.
        # Se não houver um local válido, o agente não pode ser criado da forma como está.
        # A função criar_agente espera um nome de local válido.
        # Se 'local_atual' for None ou inválido, a criação falhará.
        # Isso é um ponto a ser melhorado na robustez do save/load.
        # Por enquanto, se 'local_atual' for None, a chamada a criar_agente falhará.
        # Devemos garantir que 'local_atual' no JSON seja sempre um nome de local existente
        # ou ter uma lógica de fallback (ex: primeiro local da lista).
        # Para o escopo atual, vamos assumir que os dados salvos são consistentes.
        # Se local_atual_nome for None, criar_agente vai falhar.
        # A melhor abordagem é garantir que `local_atual` seja sempre um nome válido no JSON,
        # ou modificar `criar_agente` para aceitar `local: Optional[str]`.
        # A dataclass Agente já tem `local_atual: Optional[Local]`.
        # `criar_agente` define `local_obj = locais.get(local)`. Se `local` é None, `get(None)` é None.
        # Então `local_obj.adicionar_agente(self)` falhará.
        # A correção mais simples é garantir que `criar_agente` possa lidar com `local_obj` sendo None,
        # ou que o agente seja criado sem local se `local_atual_nome` for None.
        # Por agora, vamos manter a lógica e se `local_atual_nome` for None, `criar_agente` falhará.

        agente_local_nome = info.get("local_atual")
        if not agente_local_nome and locais: # Se não há local salvo e há locais disponíveis
            agente_local_nome = list(locais.keys())[0] # Usa o primeiro local como fallback
            logger.warning(f"Agente '{info['nome']}' não tinha local_atual salvo. Atribuído ao local padrão '{agente_local_nome}'.")
        elif not agente_local_nome and not locais:
            logger.error(f"Não há locais definidos. Impossível carregar agente '{info['nome']}' sem um local_atual.")
            continue # Pula este agente


        ag = criar_agente(
            info["nome"],
            info["funcao"],
            info["modelo_llm"],
            agente_local_nome, # Usar o nome do local obtido/fallback
            info.get("objetivo_atual", ""),
        )
        ag.historico_acoes = info.get("historico_acoes", [])
        ag.historico_interacoes = info.get("historico_interacoes", [])
        ag.historico_locais = info.get("historico_locais", ag.historico_locais)
        ag.feedback_ceo = info.get("feedback_ceo", "")
        ag.estado_emocional = info.get("estado_emocional", 0)

    # Carregar histórico de ideias
    carregar_historico_ideias(arquivo_historico_ideias)
        ag = criar_agente(
            info["nome"],
            info["funcao"],
            info["modelo_llm"],
            info.get("local_atual") or "",
            info.get("objetivo_atual", ""),
        )
        ag.historico_acoes = info.get("historico_acoes", [])
        ag.historico_interacoes = info.get("historico_interacoes", [])
        ag.historico_locais = info.get("historico_locais", ag.historico_locais)
        ag.feedback_ceo = info.get("feedback_ceo", "")
        ag.estado_emocional = info.get("estado_emocional", 0)


def calcular_lucro_ciclo() -> dict:
    """Atualiza o saldo global de acordo com receitas e custos do ciclo."""
    global saldo
    receita = 0.0
    for ag in agentes.values():
        if ag.historico_acoes and ag.historico_acoes[-1].endswith("ok"):
            receita += 10.0

    custos_salario = len(agentes) * 5.0
    custos_recursos = sum(len(ag.local_atual.inventario) for ag in agentes.values() if ag.local_atual)
    custos = custos_salario + custos_recursos
    saldo += receita - custos

    if MODO_VIDA_INFINITA:
        saldo += 1000.0 # Generous income boost
        registrar_evento(f"VIDA INFINITA: Saldo aumentado em 1000.0. Saldo atual: {saldo:.2f}")
        # Optionally, ensure it doesn't go below a very high floor
        if saldo < 5000.0:
             saldo = 5000.0
             registrar_evento(f"VIDA INFINITA: Saldo restaurado para 5000.0.")
    else:
        if saldo < 10.0:
            saldo = 10.0
            registrar_evento(f"Saldo mínimo de 10.0 restaurado para garantir continuidade. Saldo atual: {saldo:.2f}")

    historico_saldo.append(saldo)
    return {"saldo": saldo, "receita": receita, "custos": custos}


def gerar_prompt_dinamico(agente: Agente) -> str:
    """Gera uma descrição textual da situação atual de um agente."""

    if agente.local_atual is None:
        return f"Agente {agente.nome} está sem local definido."

    local = agente.local_atual
    colegas = [a.nome for a in local.agentes_presentes if a is not agente]

    partes = [
        f"Agente: {agente.nome}",
        f"Função: {agente.funcao}",
        f"Local: {local.nome}",
        f"Descrição do local: {local.descricao}",
        (
            "Colegas presentes: "
            + (", ".join(colegas) if colegas else "Nenhum")
        ),
        (
            "Inventário disponível: "
            + (", ".join(local.inventario) if local.inventario else "Nenhum")
        ),
        (
            "Últimas ações: "
            + (" | ".join(agente.historico_acoes[-3:]) if agente.historico_acoes else "Nenhuma")
        ),
        (
            "Últimas interações: "
            + (" | ".join(agente.historico_interacoes[-3:]) if agente.historico_interacoes else "Nenhuma")
        ),
        (
            "Últimos locais: "
            + (" -> ".join(agente.historico_locais[-2:]) if agente.historico_locais else "Nenhum")
        ),
        f"Objetivo atual: {agente.objetivo_atual or 'Nenhum'}",
        "Objetivo principal: maximizar o lucro da empresa de forma autônoma e criativa",
        f"Feedback do CEO: {agente.feedback_ceo or 'Nenhum'}",
        f"Estado emocional: {agente.estado_emocional}",
    ]
    return "\n".join(partes)


def gerar_prompt_decisao(agente: Agente) -> str:
    """Monta um prompt completo solicitando a próxima ação do agente.

    O prompt descreve o contexto atual e instrui a IA a escolher entre
    ficar na sala, mover-se para outro local ou enviar uma mensagem para
    um colega. A resposta deve ser unicamente em JSON seguindo o formato
    exemplificado na mensagem.
    """

    if agente.local_atual is None:
        contexto = f"Agente {agente.nome} está sem local definido."
    else:
        local = agente.local_atual
        colegas = [a.nome for a in local.agentes_presentes if a is not agente]
        contexto = "\n".join(
            [
                f"Agente: {agente.nome}",
                f"Função: {agente.funcao}",
                f"Local: {local.nome} - {local.descricao}",
                (
                    "Colegas presentes: "
                    + (", ".join(colegas) if colegas else "Nenhum")
                ),
                (
                    "Inventário disponível: "
                    + (", ".join(local.inventario) if local.inventario else "Nenhum")
                ),
                (
                    "Outros locais disponíveis: "
                    + ", ".join(nome for nome in locais if nome != local.nome)
                ),
                (
                    "Ações recentes: "
                    + (" | ".join(agente.historico_acoes[-3:]) if agente.historico_acoes else "Nenhuma")
                ),
                (
                    "Interações recentes: "
                    + (" | ".join(agente.historico_interacoes[-3:]) if agente.historico_interacoes else "Nenhuma")
                ),
                (
                    "Últimos locais: "
                    + (" -> ".join(agente.historico_locais[-2:]) if agente.historico_locais else "Nenhum")
                ),
                f"Objetivo: {agente.objetivo_atual or 'Nenhum'}",
                "Objetivo principal: maximizar o lucro da empresa de forma autônoma e criativa",
                f"Feedback do CEO: {agente.feedback_ceo or 'Nenhum'}",
                f"Estado emocional: {agente.estado_emocional}",
            ]
        )

    instrucoes = (
        "Seu objetivo final é maximizar o lucro da empresa de forma autônoma e criativa.\n"
        "Escolha UMA das ações a seguir e responda apenas em JSON:\n"
        "1. 'ficar' - permanecer no local atual.\n"
        "2. 'mover' - ir para outro local. Use o campo 'local' com o destino.\n"
        "3. 'mensagem' - enviar uma mensagem. Use 'destinatario' e 'texto'.\n"
        "Exemplos:\n"
        '{"acao": "ficar"}\n'
        '{"acao": "mover", "local": "Sala de Reunião"}\n'
        '{"acao": "mensagem", "destinatario": "Bob", "texto": "bom dia"}'
    )

    return f"{contexto}\n\n{instrucoes}"


def chamar_openrouter_api(agente: Agente, prompt: str) -> str:
    """Envia um prompt para a API OpenRouter e retorna a resposta do LLM.

    Args:
        agente: O objeto Agente para o qual o prompt é destinado.
        prompt: O prompt textual a ser enviado para o LLM.

    Returns:
        A resposta textual do LLM (geralmente uma string JSON representando
        a decisão do agente) ou uma string JSON de erro em caso de falha.

    Behavior:
        - Applies a pre-call delay defined by `OPENROUTER_CALL_DELAY_SECONDS`.
        - Implements a retry mechanism for API calls:
            - Max retries: Defined by `MAX_RETRIES` (currently 3).
            - Initial backoff delay: `INITIAL_BACKOFF_DELAY` (e.g., 1 second).
            - Backoff strategy: Exponential (delay = initial_delay * 2^attempt).
            - Retryable status codes: Defined in `RETRYABLE_STATUS_CODES` (e.g., 429, 500s).
        - Logs errors and retry attempts.
        - Returns JSON error messages for persistent failures or non-retryable issues.

    Raises:
        Não lança exceções diretamente, mas retorna strings JSON de erro.
    """
    # Apply a fixed delay before every API call, configured globally.
    # This helps in managing request rates and can be used for debugging.
    time.sleep(OPENROUTER_CALL_DELAY_SECONDS)

    logging.debug(f"Iniciando chamada para OpenRouter API para o agente {agente.nome} com modelo {agente.modelo_llm}.")
    logging.debug(f"Prompt enviado para OpenRouter (modelo {agente.modelo_llm}):\n{prompt}")

    MAX_RETRIES = 3
    INITIAL_BACKOFF_DELAY = 1  # segundos
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

    api_key = obter_api_key()
    if not api_key:
        logging.error("OPENROUTER_API_KEY não configurada.")
        return json.dumps({"error": "API key not found", "details": "OpenRouter API key is missing or not configured."})

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": agente.modelo_llm,
        "messages": [{"role": "user", "content": prompt}],
    }

    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            logging.debug(f"Tentativa {attempt + 1}: Resposta crua da OpenRouter (status {response.status_code}): {response.text}")

            if response.status_code == 200:
                response_data = response.json()
                if response_data.get("choices") and \
                   isinstance(response_data["choices"], list) and \
                   len(response_data["choices"]) > 0 and \
                   response_data["choices"][0].get("message") and \
                   isinstance(response_data["choices"][0]["message"], dict) and \
                   response_data["choices"][0]["message"].get("content"):
                    content = response_data['choices'][0]['message']['content']
                    return content
                else:
                    logging.error("Estrutura de resposta da API OpenRouter inesperada: %s", response_data)
                    return json.dumps({"error": "Invalid response structure", "details": "Unexpected API response format."})

            elif response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < MAX_RETRIES - 1:
                    backoff_time = INITIAL_BACKOFF_DELAY * (2 ** attempt)
                    logging.warning(
                        f"Erro {response.status_code} na tentativa {attempt + 1} para o agente {agente.nome}. "
                        f"Tentando novamente em {backoff_time} segundos..."
                    )
                    time.sleep(backoff_time)
                    continue
                else:
                    logging.error(
                        f"Erro {response.status_code} na API OpenRouter para o agente {agente.nome} após {MAX_RETRIES} tentativas. "
                        f"Detalhes: {response.text}"
                    )
                    return json.dumps({"error": f"Erro na API OpenRouter: {response.status_code}", "details": response.text})
            else:
                # Erro não recuperável ou não previsto para retry
                logging.error(
                    f"Erro não recuperável {response.status_code} na API OpenRouter para o agente {agente.nome}. "
                    f"Detalhes: {response.text}"
                )
                response.raise_for_status() # Isso vai levantar um HTTPError para ser pego pelo RequestException abaixo
                # No caso de não levantar, retornamos o erro genérico.
                return json.dumps({"error": f"Erro na API OpenRouter: {response.status_code}", "details": response.text})

        except requests.exceptions.Timeout as e:
            logging.error(f"Timeout na tentativa {attempt + 1} para a API OpenRouter (agente {agente.nome}): {e}")
            if attempt < MAX_RETRIES - 1:
                backoff_time = INITIAL_BACKOFF_DELAY * (2 ** attempt)
                logging.info(f"Tentando novamente em {backoff_time} segundos...")
                time.sleep(backoff_time)
                continue
            else:
                logging.error(f"Timeout final após {MAX_RETRIES} tentativas para o agente {agente.nome}: {e}")
                return json.dumps({"error": "API call failed", "details": "Request timed out after multiple retries."})
        except requests.exceptions.RequestException as e:
            logging.error(f"Erro de requisição na tentativa {attempt + 1} para a API OpenRouter (agente {agente.nome}): {e}")
            # Para erros de rede genéricos, podemos ou não querer tentar novamente.
            # Por agora, vamos tentar novamente para qualquer RequestException que não seja Timeout.
            if attempt < MAX_RETRIES - 1:
                backoff_time = INITIAL_BACKOFF_DELAY * (2 ** attempt)
                logging.info(f"Tentando novamente em {backoff_time} segundos...")
                time.sleep(backoff_time)
                continue
            else:
                logging.error(f"Erro final de requisição após {MAX_RETRIES} tentativas para o agente {agente.nome}: {e}")
                return json.dumps({"error": "API call failed", "details": str(e)})
        except json.JSONDecodeError as e:
            # Este erro ocorre se a resposta (mesmo com status 200) não for JSON válido. Não é retryable.
            logging.error(f"Erro ao decodificar JSON da resposta da API OpenRouter para o agente {agente.nome}: {e}. Resposta: {response.text if 'response' in locals() and hasattr(response, 'text') else 'N/A'}")
            return json.dumps({"error": "API call failed", "details": "Invalid JSON response from API."})
        except (KeyError, IndexError, TypeError) as e:
            # Erro na estrutura da resposta JSON. Não é retryable.
            logging.error(f"Erro ao processar estrutura da resposta da API OpenRouter para o agente {agente.nome}: {e}")
            return json.dumps({"error": "Invalid response structure", "details": str(e)})

    # Caso o loop termine sem retornar (o que não deveria acontecer com a lógica atual)
    logging.error(f"A função chamar_openrouter_api terminou inesperadamente para o agente {agente.nome}.")
    return json.dumps({"error": "API call failed", "details": "Unknown error after retries."})


def enviar_para_llm(agente: Agente, prompt: str) -> str:
    registrar_evento(f"Prompt para {agente.nome}")
    """Envia o prompt para o modelo LLM do agente usando a API OpenRouter.

    Args:
        agente: O objeto `Agente` que está tomando a decisão.
        prompt: O prompt textual formatado para guiar a decisão do LLM.

    Returns:
        A resposta do LLM (normalmente uma string JSON) conforme recebida
        de `chamar_openrouter_api`. Esta resposta será então processada
        por `executar_resposta`.
    """
    # registrar_evento(f"Prompt para {agente.nome}") # Evento já registrado em gerar_prompt_decisao ou similar

    logging.info(f"Enviando prompt para LLM {agente.modelo_llm} para o agente {agente.nome}.")
    resposta_llm = chamar_openrouter_api(agente, prompt)

    registrar_evento(f"Resposta recebida de {agente.modelo_llm} para {agente.nome}: {resposta_llm[:200]}...") # Log truncado
    logging.debug(f"Resposta completa de {agente.modelo_llm} para {agente.nome}: {resposta_llm}")
    return resposta_llm


def executar_resposta(agente: Agente, resposta: str) -> None:
    """Interpreta e executa a ação contida na resposta do LLM para um agente.

    A função é projetada para ser robusta, lidando com diversos cenários de erro:
    1.  Erros pré-definidos pela função `chamar_openrouter_api` (falhas na API, etc.).
    2.  Respostas que não são JSON válidos.
    3.  JSONs que não contêm uma ação ('acao') válida ou esperada.
    4.  Ações que possuem parâmetros inválidos (ex: local de 'mover' inexistente).

    Em muitos casos de erro, a função aplica um fallback para a ação 'ficar',
    garantindo que o agente execute uma ação segura. Todas as etapas, erros e
    fallbacks são devidamente logados.
    """

    # 1. Handle API Error JSON from chamar_openrouter_api
    # Simple string check for known error structures before JSON parsing
    if '"error": "API call failed"' in resposta or \
       '"error": "Invalid response structure"' in resposta or \
       '"error": "API key not found"' in resposta:
        # Log já feito em chamar_openrouter_api, aqui apenas registramos o evento e ação do agente
        msg_evento = f"Erro na chamada da API LLM para {agente.nome}, usando resposta de erro: {resposta}"
        registrar_evento(msg_evento)
        # logging.error(msg_evento) # O log detalhado já foi feito em chamar_openrouter_api
        agente.registrar_acao("API call error -> falha", False)
        # Decidido não aplicar fallback automático para 'ficar' aqui, pois o erro é na comunicação com LLM.
        return

    dados: Optional[dict] = None
    try:
        dados = json.loads(resposta)
    except json.JSONDecodeError:
        msg = f"Resposta JSON inválida do LLM para {agente.nome}: {resposta}"
        registrar_evento(msg)
        logging.error(msg)
        agente.registrar_acao("invalid JSON response -> falha", False)

        acao_fallback = "ficar"
        logging.warning(f"Fallback: {agente.nome} vai '{acao_fallback}' devido a JSON inválido. Resposta original: {resposta}")
        msg_ficar = f"{agente.nome} permanece em {agente.local_atual.nome} (fallback por JSON inválido)."
        registrar_evento(msg_ficar)
        logging.info(msg_ficar)
        agente.registrar_acao(f"{acao_fallback} (fallback JSON) -> ok", True)
        return

    acao = dados.get("acao")
    valid_actions = ["ficar", "mover", "mensagem"]

    if acao not in valid_actions:
        msg = f"Acao invalida ('{acao}') ou ausente na resposta do LLM para {agente.nome}. Resposta: {resposta}"
        registrar_evento(msg)
        logging.warning(msg)
        agente.registrar_acao(f"acao invalida '{acao}' -> falha", False)

        acao_fallback_str = "ficar"
        logging.warning(f"Fallback: {agente.nome} vai '{acao_fallback_str}' devido à ação inválida '{acao}'. Resposta original: {resposta}")
        msg_ficar_direct = f"{agente.nome} permanece em {agente.local_atual.nome} (fallback por ação '{acao}' inválida)."
        registrar_evento(msg_ficar_direct)
        logging.info(msg_ficar_direct)
        agente.registrar_acao(f"{acao_fallback_str} (fallback acao) -> ok", True)
        return

    # Log da ação escolhida antes da execução
    if acao == "ficar":
        logging.info(f"{agente.nome} decidiu 'ficar' em {agente.local_atual.nome if agente.local_atual else 'local desconhecido'}.")
    elif acao == "mover":
        destino = dados.get("local", "destino desconhecido")
        logging.info(f"{agente.nome} decidiu 'mover' para '{destino}'.")
    elif acao == "mensagem":
        destinatario = dados.get("destinatario", "destinatário desconhecido")
        texto_msg = dados.get("texto", "")
        logging.info(f"{agente.nome} decidiu 'mensagem' para '{destinatario}' com texto: '{texto_msg[:50]}...'")


    if acao == "ficar":
        msg = f"{agente.nome} permanece em {agente.local_atual.nome}."
        registrar_evento(msg)
        logging.info(msg)
        agente.registrar_acao("ficar -> ok", True)
    elif acao == "mover":
        destino = dados.get("local")
        if not isinstance(destino, str) or not destino:
            msg = (
                f"Tentativa de mover {agente.nome} para destino inválido (ausente ou formato incorreto): {destino}."
            )
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(
                f"mover para '{destino}' -> falha (destino invalido)", False
            )

            msg_ficar_fallback_mover = f"{agente.nome} permanece em {agente.local_atual.nome} (fallback de 'mover' por destino inválido)."
            registrar_evento(msg_ficar_fallback_mover)
            logging.info(msg_ficar_fallback_mover)
            agente.registrar_acao("ficar (fallback mover) -> ok", True)
        elif destino not in locais:
            msg = f"Destino {destino} não encontrado para {agente.nome}."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(
                f"mover para {destino} -> falha (local nao existe)", False
            )

            msg_ficar_fallback_local_inexistente = f"{agente.nome} permanece em {agente.local_atual.nome} (fallback de 'mover' - local '{destino}' inexistente)."
            registrar_evento(msg_ficar_fallback_local_inexistente)
            logging.info(msg_ficar_fallback_local_inexistente)
            agente.registrar_acao("ficar (fallback mover local) -> ok", True)
        else:
            mover_agente(agente.nome, destino)
            msg = f"{agente.nome} moveu-se para {destino}."
            registrar_evento(msg)
            logging.info(msg)
            agente.registrar_acao(f"mover para {destino} -> ok", True)
    elif acao == "mensagem":
        destinatario = dados.get("destinatario")
        texto = dados.get("texto")

        if not isinstance(destinatario, str) or not destinatario or \
           not isinstance(texto, str) or texto is None:
            msg = f"Mensagem de {agente.nome} com destinatário ou texto inválido/ausente. Dest: '{destinatario}', Texto: '{texto}'."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(
                f"mensagem para {destinatario} -> falha (dados invalidos)", False
            )

            msg_ficar_fallback_msg = f"{agente.nome} permanece em {agente.local_atual.nome} (fallback de 'mensagem' por dados inválidos)."
            registrar_evento(msg_ficar_fallback_msg)
            logging.info(msg_ficar_fallback_msg)
            agente.registrar_acao("ficar (fallback mensagem) -> ok", True)
        elif destinatario not in agentes:
            msg = f"Destinatário '{destinatario}' da mensagem de {agente.nome} não encontrado."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(
                f"mensagem para {destinatario} -> falha (destinatario nao existe)",
                False,
            )

            msg_ficar_fallback_msg_dest_inexistente = f"{agente.nome} permanece em {agente.local_atual.nome} (fallback de 'mensagem' - destinatário '{destinatario}' inexistente)."
            registrar_evento(msg_ficar_fallback_msg_dest_inexistente)
            logging.info(msg_ficar_fallback_msg_dest_inexistente)
            agente.registrar_acao("ficar (fallback msg dest) -> ok", True)
        else:
            msg = f"{agente.nome} envia mensagem para {destinatario}: {texto}"
            registrar_evento(msg)
            logging.info(msg) # Log da ação de mensagem já informa os detalhes.
            agente.historico_interacoes.append(f"para {destinatario}: {texto}")
            if len(agente.historico_interacoes) > 3:
                agente.historico_interacoes = agente.historico_interacoes[-3:]
            agente.registrar_acao(f"mensagem para {destinatario} -> ok", True)


# ---------------------------------------------------------------------------
# Exemplo de uso
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    """Demonstra a inicialização e alguns ciclos da simulação.

    Este exemplo configura o logging, inicializa a empresa (agentes e locais),
    e executa alguns ciclos de simulação onde os agentes tomam decisões
    baseadas em LLM.
    """

    # Configuração básica de logging para ver INFO e DEBUG messages.
    # Em uma aplicação real, isso pode ser mais configurável.
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s')

    from rh import modulo_rh
    # A importação de executar_ciclo_criativo é feita aqui para evitar importação circular no topo do arquivo,
    # já que ciclo_criativo importa empresa_digital (ed).
    # A definição de Ideia foi movida para core_types.py para quebrar a dependência circular de tipos.
    # As funções salvar_historico_ideias e carregar_historico_ideias ainda são importadas de ciclo_criativo.
    # Isso é aceitável, pois são chamadas de função, não dependências de tipo na definição de classes globais.
    import ciclo_criativo as cc

    inicializar_automaticamente()
    # Carregar dados salvos, se existirem, após a inicialização padrão (que pode criar defaults)
    # ou antes, dependendo da lógica desejada (sobrescrever defaults com salvos).
    # Para este exemplo, vamos carregar após, o que significa que se os arquivos não existirem,
    # a inicialização automática prevalece. Se existirem, eles sobrescrevem.
    # Idealmente, carregar_dados deveria limpar o estado antes de carregar.
    # A lógica atual de carregar_dados já zera agentes e locais.
    # E carregar_historico_ideias também zera o histórico antes de carregar.

    # Tentativa de carregar dados salvos. Se não existirem, a empresa continua com a inicialização automática.
    # Definir nomes de arquivos padrão para salvar/carregar no exemplo.
    save_file_agentes = "agentes_estado.json"
    save_file_locais = "locais_estado.json"
    save_file_ideias = "historico_ideias.json"

    try:
        carregar_dados(save_file_agentes, save_file_locais, save_file_ideias)
        logger.info("Dados da simulação anterior carregados com sucesso.")
    except FileNotFoundError:
        logger.info("Nenhum dado salvo encontrado. Iniciando com uma nova simulação.")
    except Exception as e:
        logger.error(f"Erro ao carregar dados salvos: {e}. Iniciando com uma nova simulação.")


    for ciclo in range(1, 4):
        logging.info("=== Ciclo %d ===", ciclo)

        if not tarefas_pendentes:
            if MODO_VIDA_INFINITA:
                novas_tarefas = [
                    "Expandir para novo mercado internacional",
                    "Desenvolver funcionalidade revolucionária X",
                    "Criar campanha de marketing viral",
                    "Otimizar infraestrutura para escala global",
                    "Pesquisar aquisição de startup promissora"
                ]
                registrar_evento("VIDA INFINITA: Gerando 5 tarefas automáticas.")
            else:
                novas_tarefas = [
                    "Pesquisar novas tecnologias disruptivas",
                    "Analisar feedback de clientes e propor melhorias"
                ]
                registrar_evento("Gerando 2 tarefas automáticas padrão.")

            for nt in novas_tarefas:
                adicionar_tarefa(nt)
                registrar_evento(f"Tarefa automática gerada: {nt}")

        modulo_rh.verificar()
        executar_ciclo_criativo()

        # Selecionar um subconjunto de agentes para processamento LLM neste ciclo
        # para gerenciar custos de API e tempo de processamento.
        todos_os_agentes = list(agentes.values())
        # Embaralhar a lista de agentes para garantir que diferentes agentes sejam escolhidos
        # em ciclos diferentes, promovendo maior variedade nas interações.
        random.shuffle(todos_os_agentes)
        # Selecionar o número máximo de agentes definido por MAX_LLM_AGENTS_PER_CYCLE.
        agentes_para_llm = todos_os_agentes[:MAX_LLM_AGENTS_PER_CYCLE]

        logging.info(
            f"Selecionados {len(agentes_para_llm)} de {len(todos_os_agentes)} agentes "
            f"para processamento LLM neste ciclo (limite: {MAX_LLM_AGENTS_PER_CYCLE})."
        )

        for agente in agentes_para_llm: # Iterar apenas sobre o subconjunto selecionado.
            prompt = gerar_prompt_decisao(agente)
            resposta = enviar_para_llm(agente, prompt)
            executar_resposta(agente, resposta)

        # O cálculo de lucro e outras lógicas de fim de ciclo podem continuar considerando todos os agentes
        # ou apenas os que interagiram, dependendo da lógica de negócio desejada.
        # Por ora, mantemos como estava, afetando apenas quem toma decisão via LLM.
        info = calcular_lucro_ciclo()
        logging.info("Saldo apos ciclo %d: %.2f", ciclo, info["saldo"])

    # Salvar estado final da empresa
    try:
        salvar_dados(save_file_agentes, save_file_locais, save_file_ideias)
        logger.info("Estado da simulação salvo com sucesso.")
    except Exception as e:
        logger.error(f"Erro ao salvar estado da simulação: {e}")
