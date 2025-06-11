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
import uuid # Adicionado para gerar IDs para tarefas antigas, se necessário
# import json # Já importado acima
# import logging # Já importado acima

# Imports do ciclo_criativo para persistência do histórico de ideias e serviços
# e de core_types para a definição de Ideia e Service.
from .core_types import Ideia, Service # Service é potencialmente usado aqui se empresa_digital manipular serviços diretamente

# A funcao para buscar a API key deve vir de openrouter_utils para evitar
# dependencias circulares com o modulo `api` utilizado nos testes e no backend.
from openrouter_utils import obter_api_key

# Módulo ciclo_criativo importado com alias para evitar conflitos e usado para acessar seus membros.
import ciclo_criativo as cc
# Acesso direto a historico_ideias e historico_servicos para conveniência onde usado.
from ciclo_criativo import historico_ideias, historico_servicos # Ensure these are used if direct access is intended
from dataclasses import asdict # For serializing dataclass objects like Task

logger = logging.getLogger(__name__)

# Permite ativar o modo Vida Infinita via variavel de ambiente
MODO_VIDA_INFINITA: bool = os.environ.get("MODO_VIDA_INFINITA", "0") == "1"
# Define a factor for converting service effort hours to simulation time (e.g., cycles or time units)
# This could be configured elsewhere, e.g., based on MODO_VIDA_INFINITA or other sim params
# If 1 cycle = 1 day, and agents work 8 hours a day, this factor could be 1.0
# If 1 cycle is shorter, this factor would be smaller.
# Let's assume 1 cycle can achieve 8 hours of work for simplicity in this factor.
# A lower value means services take more cycles to complete for the same effort_hours.
HOURS_PER_CYCLE_FACTOR = 8.0
# In MODO_VIDA_INFINITA, perhaps services complete faster to accelerate progress
HOURS_PER_CYCLE_FACTOR_VIDA_INFINITA = 16.0

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
from .core_types import Task # Import Task dataclass
tarefas_pendentes: List[Task] = []

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
    actions_successful_for_objective: int = 0 # New field for tracking task progress
    cycles_idle: int = 0 # New field for tracking Executor idle cycles

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

    adicionar_tarefa("Planejar estratégia de lançamento") # Uses the new function
    # logging.info already done by adicionar_tarefa


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


def adicionar_tarefa(descricao_tarefa: str) -> Task:
    """Cria um objeto Task e o registra na lista de tarefas pendentes."""
    nova_tarefa = Task(description=descricao_tarefa)
    tarefas_pendentes.append(nova_tarefa)
    registrar_evento(f"Nova tarefa '{descricao_tarefa}' adicionada com status 'todo'. ID: {nova_tarefa.id}")
    logger.info(f"Nova tarefa '{descricao_tarefa}' (ID: {nova_tarefa.id}) adicionada com status 'todo'.")
    return nova_tarefa


def salvar_dados(
    arquivo_agentes: str,
    arquivo_locais: str,
    arquivo_historico_ideias: str = "historico_ideias.json",
    arquivo_historico_servicos: str = "servicos.json",
    arquivo_saldo: str = "saldo.json",
    arquivo_tarefas: str = "tarefas.json",
    arquivo_eventos: str = "eventos.json"
) -> None:
    """Salva os dicionários globais de agentes, locais, históricos, finanças, tarefas e eventos em arquivos JSON."""

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
    # Salvar histórico de serviços
    salvar_historico_servicos(arquivo_historico_servicos)

    # Salvar saldo e historico_saldo
    try:
        with open(arquivo_saldo, "w", encoding="utf-8") as f:
            json.dump({"saldo": saldo, "historico_saldo": historico_saldo}, f, ensure_ascii=False, indent=2)
        logger.info(f"Dados de saldo salvos em {arquivo_saldo}")
    except IOError as e:
        logger.error(f"Erro ao salvar dados de saldo em {arquivo_saldo}: {e}")

    # Salvar tarefas_pendentes (List[Task])
    try:
        dados_tarefas = [asdict(task) for task in tarefas_pendentes]
        with open(arquivo_tarefas, "w", encoding="utf-8") as f:
            json.dump(dados_tarefas, f, ensure_ascii=False, indent=2)
        logger.info(f"Tarefas pendentes salvas em {arquivo_tarefas}")
    except IOError as e:
        logger.error(f"Erro ao salvar tarefas pendentes em {arquivo_tarefas}: {e}")
    except TypeError as e: # Handle cases where asdict might fail if Task objects are not simple dataclasses
        logger.error(f"Erro de tipo ao serializar tarefas: {e}. Verifique a estrutura dos objetos Task.")


    # Salvar historico_eventos (List[str])
    try:
        with open(arquivo_eventos, "w", encoding="utf-8") as f:
            json.dump(historico_eventos, f, ensure_ascii=False, indent=2)
        logger.info(f"Histórico de eventos salvo em {arquivo_eventos}")
    except IOError as e:
        logger.error(f"Erro ao salvar histórico de eventos em {arquivo_eventos}: {e}")


def carregar_dados(
    arquivo_agentes: str,
    arquivo_locais: str,
    arquivo_historico_ideias: str = "historico_ideias.json",
    arquivo_historico_servicos: str = "servicos.json",
    arquivo_saldo: str = "saldo.json",
    arquivo_tarefas: str = "tarefas.json",
    arquivo_eventos: str = "eventos.json"
) -> None:
    """Carrega arquivos JSON recriando os dicionários de agentes, locais, históricos, finanças, tarefas e eventos."""

    global agentes, locais, saldo, historico_saldo, tarefas_pendentes, historico_eventos
    # Resetar estados que serão totalmente preenchidos pelos arquivos
    agentes = {}
    locais = {}
    # Saldo, historico_saldo, tarefas_pendentes, historico_eventos são resetados/inicializados abaixo
    # antes de carregar ou com defaults se o arquivo não existir.

    # Carregar saldo e historico_saldo
    try:
        with open(arquivo_saldo, "r", encoding="utf-8") as f:
            dados_saldo_json = json.load(f)
            saldo = dados_saldo_json.get("saldo", 0.0)
            historico_saldo = dados_saldo_json.get("historico_saldo", [])
        logger.info(f"Dados de saldo carregados de {arquivo_saldo}.")
    except FileNotFoundError:
        logger.warning(f"Arquivo de saldo '{arquivo_saldo}' não encontrado. Usando saldo inicial padrão (0.0) e histórico vazio.")
        saldo = 0.0
        historico_saldo = []
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do arquivo de saldo '{arquivo_saldo}': {e}. Usando defaults.")
        saldo = 0.0
        historico_saldo = []
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar arquivo de saldo '{arquivo_saldo}': {e}. Usando defaults.")
        saldo = 0.0
        historico_saldo = []


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
    # Carregar histórico de serviços
    carregar_historico_servicos(arquivo_historico_servicos)

    # Carregar tarefas_pendentes
    try:
        with open(arquivo_tarefas, "r", encoding="utf-8") as f:
            dados_tarefas_json = json.load(f)

        temp_tarefas_pendentes = []
        for task_data in dados_tarefas_json:
            if isinstance(task_data, str): # Backward compatibility: old format was List[str]
                task_obj = Task(description=task_data, status="todo") # Default status
                registrar_evento(f"Tarefa antiga '{task_data}' convertida para novo formato Task ID: {task_obj.id}.")
                logger.info(f"Tarefa antiga '{task_data}' convertida para novo formato Task (ID: {task_obj.id}).")
            elif isinstance(task_data, dict): # New format: List[Dict]
                # Ensure all necessary fields are present or provide defaults
                # This is important if the Task dataclass evolves
                task_description = task_data.get("description")
                if not task_description:
                    logger.warning(f"Tarefa carregada sem descrição: {task_data.get('id', 'ID Desconhecido')}. Pulando.")
                    continue

                task_obj = Task(
                    id=task_data.get("id", uuid.uuid4().hex), # Generate new ID if missing
                    description=task_description,
                    status=task_data.get("status", "todo"),
                    history=task_data.get("history", [])
                )
            else:
                logger.warning(f"Formato de dado de tarefa desconhecido encontrado: {type(task_data)}. Pulando.")
                continue
            temp_tarefas_pendentes.append(task_obj)
        tarefas_pendentes = temp_tarefas_pendentes
        logger.info(f"Tarefas pendentes carregadas de {arquivo_tarefas}. {len(tarefas_pendentes)} tarefas carregadas.")
    except FileNotFoundError:
        logger.warning(f"Arquivo de tarefas '{arquivo_tarefas}' não encontrado. Lista de tarefas pendentes iniciada vazia.")
        tarefas_pendentes = []
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do arquivo de tarefas '{arquivo_tarefas}': {e}. Lista de tarefas vazia.")
        tarefas_pendentes = []
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar arquivo de tarefas '{arquivo_tarefas}': {e}. Lista de tarefas vazia.")
        tarefas_pendentes = []

    # Carregar historico_eventos
    try:
        with open(arquivo_eventos, "r", encoding="utf-8") as f:
            loaded_eventos = json.load(f)
            if isinstance(loaded_eventos, list):
                historico_eventos = loaded_eventos
            else:
                logger.error(f"Arquivo de eventos '{arquivo_eventos}' não contém uma lista. Histórico de eventos iniciado vazio.")
                historico_eventos = []
        logger.info(f"Histórico de eventos carregado de {arquivo_eventos}. {len(historico_eventos)} eventos carregados.")
    except FileNotFoundError:
        logger.warning(f"Arquivo de eventos '{arquivo_eventos}' não encontrado. Histórico de eventos iniciado vazio.")
        historico_eventos = []
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do arquivo de eventos '{arquivo_eventos}': {e}. Histórico de eventos vazio.")
        historico_eventos = []
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar arquivo de eventos '{arquivo_eventos}': {e}. Histórico de eventos vazio.")
        historico_eventos = []


def calcular_lucro_ciclo() -> dict:
    """Atualiza o saldo global de acordo com receitas e custos do ciclo."""
    global saldo
    receita = 0.0
    for ag in agentes.values():
        if ag.historico_acoes and ag.historico_acoes[-1].endswith("ok"):
            receita += 10.0

    custos_salario = len(agentes) * 5.0
    custos_recursos = sum(len(ag.local_atual.inventario) for ag in agentes.values() if ag.local_atual and ag.local_atual.inventario)
    custos = custos_salario + custos_recursos

    # Calcular receita de serviços concluídos
    receita_servicos = 0.0
    # historico_servicos é importado diretamente de ciclo_criativo
    for servico in historico_servicos:
        if servico.status == "completed" and not servico.revenue_calculated:
            if servico.pricing_model == "fixed_price":
                receita_servicos += servico.price_amount
                registrar_evento(f"Receita de R${servico.price_amount:.2f} adicionada pelo serviço de preço fixo '{servico.service_name}'.")
            elif servico.pricing_model == "hourly_rate":
                receita_total_servico_horista = servico.price_amount * servico.estimated_effort_hours
                receita_servicos += receita_total_servico_horista
                registrar_evento(f"Receita de R${receita_total_servico_horista:.2f} adicionada pelo serviço por hora '{servico.service_name}'.")
            servico.revenue_calculated = True # Marcar para não calcular novamente

    receita_total_ciclo = receita + receita_servicos # Receita de ações de agentes + receita de serviços
    saldo += receita_total_ciclo - custos

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
    return {"saldo": saldo, "receita_total_ciclo": receita_total_ciclo, "receita_acoes_agentes": receita, "receita_servicos": receita_servicos, "custos": custos}


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

    instrucoes_base = [
        "Seu objetivo final é maximizar o lucro da empresa de forma autônoma e criativa.",
        "Escolha UMA das ações a seguir e responda apenas em JSON:",
        "1. 'ficar' - permanecer no local atual. Ex: {\"acao\": \"ficar\"}",
        "2. 'mover' - ir para outro local. Ex: {\"acao\": \"mover\", \"local\": \"Sala de Reunião\"}",
        "3. 'mensagem' - enviar uma mensagem. Ex: {\"acao\": \"mensagem\", \"destinatario\": \"Bob\", \"texto\": \"bom dia\"}",
    ]

    # Add service assignment & task proposal for CEO
    if agente.funcao.lower() == "ceo":
        # Company Status Summary
        contexto += f"\n\n--- Resumo da Empresa ---\nSaldo Atual: R${saldo:.2f}\n"

        # Active Ideas (Validated but not yet fully executed/product link might be missing)
        # historico_ideias is imported directly from ciclo_criativo
        active_ideas = [i for i in historico_ideias if i.validada and not i.executada] # Simple definition of "active"
        if active_ideas:
            contexto += "Ideias de Produto Ativas (Validadas, não Executadas):\n"
            for idx, idea in enumerate(active_ideas[:3]): # Show top 3 for brevity
                contexto += f"  - IP{idx+1}: {idea.descricao} (Autor: {idea.autor})\n"
        else:
            contexto += "Nenhuma ideia de produto ativa no momento.\n"

        # Active Services (Validated or In Progress)
        # historico_servicos is imported directly from ciclo_criativo
        active_services = [s for s in historico_servicos if s.status in ["validated", "in_progress"]]
        if active_services:
            contexto += "Serviços Ativos (Validados ou Em Progresso):\n"
            for idx, serv in enumerate(active_services[:3]): # Show top 3 for brevity
                status_detail = f"(Status: {serv.status}"
                if serv.status == "in_progress" and serv.assigned_agent_name:
                    status_detail += f", Agente: {serv.assigned_agent_name}"
                status_detail += ")"
                contexto += f"  - SV{idx+1}: {serv.service_name} {status_detail}\n"
        else:
            contexto += "Nenhum serviço ativo no momento.\n"
        contexto += "-------------------------\n"

        # Service Assignment Instructions
        servicos_para_atribuir = [s for s in historico_servicos if s.status == "validated"]
        if servicos_para_atribuir:
            instrucoes_base.append(
                "4. 'assign_service' - atribuir um serviço validado a um agente. "
                "Ex: {\"acao\": \"assign_service\", \"service_id\": \"<id_do_servico>\", \"agent_name\": \"<nome_do_agente>\"}"
            )
            contexto += "\nServiços Validados para Atribuição (lista detalhada no prompt anterior se aplicável):\n"
            for s_idx, s in enumerate(servicos_para_atribuir[:3]): # Show top 3 for brevity in this specific section
                contexto += (
                    f"  - ID: {s.id[:8]}..., Nome: {s.service_name}\n" # Short ID
                )

            agentes_disponiveis_info = []
            for ag_idx, ag_disp in enumerate(agentes.values()):
                agentes_disponiveis_info.append(f"{ag_disp.nome} (Função: {ag_disp.funcao})")

            if agentes_disponiveis_info:
                 contexto += "Agentes Disponíveis para Atribuição (resumido):\n" + ", ".join(agentes_disponiveis_info[:5]) + "\n" # Top 5

        # Task Proposal Instruction
        instrucoes_base.append(
            "5. 'propor_tarefa' - propor uma nova tarefa de alto nível para a empresa. "
            "Ex: {\"acao\": \"propor_tarefa\", \"tarefa_descricao\": \"Expandir para o mercado de chatbots educacionais.\"}"
        )

    instrucoes = "\n".join(instrucoes_base)
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
    # Adicionar 'assign_service' e 'propor_tarefa' às ações válidas
    valid_actions = ["ficar", "mover", "mensagem", "assign_service", "propor_tarefa"]

    if acao not in valid_actions:
        msg = f"Acao invalida ('{acao}') ou ausente na resposta do LLM para {agente.nome}. Resposta: {resposta}"
        registrar_evento(msg)
        logging.warning(msg)
        agente.registrar_acao(f"acao invalida '{acao}' -> falha", False)
        # Fallback para 'ficar'
        acao_fallback_str = "ficar"
        logging.warning(f"Fallback: {agente.nome} vai '{acao_fallback_str}' devido à ação inválida '{acao}'.")
        msg_ficar_direct = f"{agente.nome} permanece em {agente.local_atual.nome if agente.local_atual else 'Local Desconhecido'} (fallback por ação '{acao}' inválida)."
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
    elif acao == "assign_service":
        service_id = dados.get("service_id")
        agent_name_to_assign = dados.get("agent_name")
        logging.info(f"{agente.nome} (função: {agente.funcao}) decidiu 'assign_service' para service ID '{service_id}' ao agente '{agent_name_to_assign}'.")
    elif acao == "propor_tarefa":
        tarefa_desc = dados.get("tarefa_descricao", "Tarefa não especificada.")
        logging.info(f"{agente.nome} (função: {agente.funcao}) decidiu 'propor_tarefa': '{tarefa_desc}'.")


    # Execução da ação
    if acao == "ficar":
        msg = f"{agente.nome} permanece em {agente.local_atual.nome if agente.local_atual else 'Local Desconhecido'}."
        registrar_evento(msg)
        logging.info(msg)
        agente.registrar_acao("ficar -> ok", True)
    elif acao == "mover":
        destino = dados.get("local")
        if not isinstance(destino, str) or not destino:
            # ... (fallback logic for mover)
            msg = f"Tentativa de mover {agente.nome} para destino inválido: {destino}."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(f"mover para '{destino}' -> falha (destino invalido)", False)
            msg_ficar_fallback_mover = f"{agente.nome} permanece em {agente.local_atual.nome if agente.local_atual else 'Local Desconhecido'} (fallback de 'mover' por destino inválido)."
            registrar_evento(msg_ficar_fallback_mover)
            agente.registrar_acao("ficar (fallback mover) -> ok", True)
        elif destino not in locais:
            # ... (fallback logic for mover)
            msg = f"Destino {destino} não encontrado para {agente.nome}."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(f"mover para {destino} -> falha (local nao existe)", False)
            msg_ficar_fallback_local_inexistente = f"{agente.nome} permanece em {agente.local_atual.nome if agente.local_atual else 'Local Desconhecido'} (fallback de 'mover' - local '{destino}' inexistente)."
            registrar_evento(msg_ficar_fallback_local_inexistente)
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
        if not isinstance(destinatario, str) or not destinatario or not isinstance(texto, str) or texto is None:
            # ... (fallback logic for mensagem)
            msg = f"Mensagem de {agente.nome} com destinatário ou texto inválido/ausente."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(f"mensagem para {destinatario} -> falha (dados invalidos)", False)
            msg_ficar_fallback_msg = f"{agente.nome} permanece em {agente.local_atual.nome if agente.local_atual else 'Local Desconhecido'} (fallback de 'mensagem' por dados inválidos)."
            registrar_evento(msg_ficar_fallback_msg)
            agente.registrar_acao("ficar (fallback mensagem) -> ok", True)
        elif destinatario not in agentes:
            # ... (fallback logic for mensagem)
            msg = f"Destinatário '{destinatario}' da mensagem de {agente.nome} não encontrado."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(f"mensagem para {destinatario} -> falha (destinatario nao existe)", False)
            msg_ficar_fallback_msg_dest_inexistente = f"{agente.nome} permanece em {agente.local_atual.nome if agente.local_atual else 'Local Desconhecido'} (fallback de 'mensagem' - destinatário '{destinatario}' inexistente)."
            registrar_evento(msg_ficar_fallback_msg_dest_inexistente)
            agente.registrar_acao("ficar (fallback msg dest) -> ok", True)
        else:
            msg = f"{agente.nome} envia mensagem para {destinatario}: {texto}"
            registrar_evento(msg)
            logging.info(msg)
            agente.historico_interacoes.append(f"para {destinatario}: {texto}")
            if len(agente.historico_interacoes) > 3:
                agente.historico_interacoes = agente.historico_interacoes[-3:]
            agente.registrar_acao(f"mensagem para {destinatario} -> ok", True)

    elif acao == "assign_service":
        service_id = dados.get("service_id")
        agent_name_to_assign = dados.get("agent_name")
        service_to_assign = next((s for s in historico_servicos if s.id == service_id), None)
        assignee_agent = agentes.get(agent_name_to_assign)

        if not service_to_assign:
            msg = f"Falha ao atribuir serviço: ID '{service_id}' não encontrado por {agente.nome}."
            registrar_evento(msg)
            logging.warning(msg)
            agente.registrar_acao(f"assign_service {service_id} -> {agent_name_to_assign} -> falha (serviço não existe)", False)
        elif not assignee_agent:
            msg = f"Falha ao atribuir serviço '{service_to_assign.service_name}' por {agente.nome}: Agente '{agent_name_to_assign}' não encontrado."
            registrar_evento(msg)
            logging.warning(msg)
            agente.registrar_acao(f"assign_service {service_id} -> {agent_name_to_assign} -> falha (agente não existe)", False)
        elif service_to_assign.status != "validated":
            msg = (f"Falha ao atribuir serviço '{service_to_assign.service_name}' a {agent_name_to_assign} por {agente.nome}: "
                   f"Serviço com status '{service_to_assign.status}', esperado 'validated'.")
            registrar_evento(msg)
            logging.warning(msg)
            agente.registrar_acao(f"assign_service {service_id} -> {agent_name_to_assign} -> falha (status inválido: {service_to_assign.status})", False)
        else:
            service_to_assign.assign_agent(assignee_agent.nome, message=f"Atribuído por {agente.nome}.")
            msg = f"Serviço '{service_to_assign.service_name}' (ID: {service_id}) atribuído a {assignee_agent.nome} por {agente.nome}."
            registrar_evento(msg)
            logging.info(msg)
            agente.registrar_acao(f"assign_service {service_id} -> {assignee_agent.nome} -> ok", True)
            assignee_agent.objetivo_atual = f"Executar serviço: {service_to_assign.service_name} (ID: {service_id})"
            registrar_evento(f"Objetivo de {assignee_agent.nome} atualizado para: {assignee_agent.objetivo_atual}")

    elif acao == "propor_tarefa":
        if agente.funcao.lower() == "ceo": # Sanity check: only CEO can do this
            tarefa_descricao = dados.get("tarefa_descricao")
            if tarefa_descricao and isinstance(tarefa_descricao, str) and tarefa_descricao.strip():
                adicionar_tarefa(tarefa_descricao.strip())
                msg = f"CEO {agente.nome} propôs nova tarefa: \"{tarefa_descricao.strip()}\"."
                registrar_evento(msg)
                logging.info(msg)
                agente.registrar_acao(f"propôs tarefa: {tarefa_descricao.strip()} -> ok", True)
            else:
                msg = f"CEO {agente.nome} tentou propor tarefa, mas a descrição era inválida: '{tarefa_descricao}'."
                registrar_evento(msg)
                logging.warning(msg)
                agente.registrar_acao(f"propor_tarefa -> falha (descrição inválida)", False)
        else:
            msg = f"Agente {agente.nome} (função {agente.funcao}) tentou propor tarefa, mas não é CEO. Ação ignorada."
            registrar_evento(msg)
            logging.warning(msg)
            agente.registrar_acao(f"propor_tarefa -> falha (não autorizado)", False)

    # Após a execução bem-sucedida de uma ação (ficar, mover, mensagem),
    # verificar se o agente é um Executor e se está trabalhando em uma tarefa.
    # Este bloco é executado se agente.registrar_acao(..., sucesso=True) foi chamado.
    # Precisamos garantir que a ação foi bem sucedida antes de contar para o progresso da tarefa.
    # A chamada `agente.registrar_acao` já aconteceu acima para cada tipo de ação.
    # Vamos verificar o último histórico de ação para inferir sucesso, ou melhor,
    # o estado emocional pode ser um proxy se `registrar_acao` o atualiza consistentemente.
    # No entanto, `registrar_acao` recebe um booleano `sucesso`.
    # A lógica de task progress deve ser acionada APENAS SE a ação específica (ficar, mover, mensagem) foi bem sucedida.

    # Para simplificar, vamos assumir que se chegamos até aqui sem um fallback para "ficar" que registrou Falha,
    # a ação principal foi considerada "ok" em seu próprio bloco.
    # A forma mais limpa seria ter o bloco de `registrar_acao` retornar o status de sucesso,
    # mas para evitar refatoração profunda agora, vamos adicionar a lógica de progresso de tarefa aqui,
    # assumindo que se uma ação específica (ficar, mover, mensagem) foi executada e não caiu em um de seus próprios fallbacks
    # que chamaram `agente.registrar_acao(..., False)`, ela foi um sucesso.
    # Melhor ainda: verificar se a ÚLTIMA ação registrada foi um sucesso.
    # O `agente.registrar_acao` já ajusta `estado_emocional`.
    # E `actions_successful_for_objective` deve ser incrementado apenas se a ação principal foi um sucesso.

    # A lógica de registrar_acao(..., sucesso=True) já foi chamada para as ações acima.
    # Agora, verificamos se essa ação bem-sucedida contribui para uma tarefa.
    # A maneira mais robusta é verificar se a última ação registrada foi bem-sucedida.
    # No entanto, `agente.registrar_acao` não retorna o status de sucesso.
    # Vamos adicionar o incremento de `actions_successful_for_objective` dentro de cada bloco de ação bem-sucedida.
    # Isso já foi feito para "mensagem". Precisa ser adicionado para "ficar" e "mover" se forem bem-sucedidas.

    # REVISÃO: A lógica de incremento de `actions_successful_for_objective` já foi colocada
    # (erroneamente) apenas dentro do bloco "mensagem".
    # CORREÇÃO: Mover a lógica de incremento e checagem de conclusão de tarefa para fora dos blocos de ação específicos,
    # mas condicioná-la ao sucesso da ação principal do agente.
    # A maneira mais simples de fazer isso sem refatorar `registrar_acao` é verificar se
    # o estado emocional aumentou ou se a última entrada no histórico de ações indica sucesso.
    # Porém, a forma mais direta é fazer isso após cada chamada `agente.registrar_acao(..., True)`.

    # A estrutura atual de `executar_resposta` chama `agente.registrar_acao` em múltiplos lugares,
    # incluindo para fallbacks. Precisamos de um ponto central após uma ação principal bem-sucedida.

    # Solução: Adicionar um marcador/flag ou checar a descrição da última ação.
    # Ou, mais simples: se a ação não foi um fallback que resultou em `registrar_acao(..., False)`,
    # e o agente é um executor com task_id, incrementamos.

    # Vamos adicionar uma variável local `acao_principal_bem_sucedida`
    acao_principal_bem_sucedida = False
    if acao == "ficar" and "ficar -> ok" in agente.historico_acoes[-1]: # Verifica se a última ação foi um 'ficar' bem sucedido
        acao_principal_bem_sucedida = True
    elif acao == "mover" and "-> ok" in agente.historico_acoes[-1] and not "fallback" in agente.historico_acoes[-1]: # Movimento bem sucedido
        acao_principal_bem_sucedida = True
    elif acao == "mensagem" and "-> ok" in agente.historico_acoes[-1] and not "fallback" in agente.historico_acoes[-1]: # Mensagem bem sucedida
        acao_principal_bem_sucedida = True
    # Não contamos 'assign_service' ou 'propor_tarefa' como ações de Executor para completar *sua* tarefa.

    if acao_principal_bem_sucedida and agente.funcao.lower() == "executor" and agente.objetivo_atual.startswith("task_id:"):
        agente.actions_successful_for_objective += 1
        logger.info(f"Agente Executor {agente.nome} completou {agente.actions_successful_for_objective} ações para o objetivo {agente.objetivo_atual}.")
        if agente.actions_successful_for_objective >= 3:
            try:
                task_id_from_obj = agente.objetivo_atual.split("task_id:")[1]
                task_to_complete = next((t for t in tarefas_pendentes if t.id == task_id_from_obj), None)
                if task_to_complete and task_to_complete.status == "in_progress":
                    task_to_complete.update_status("done", f"Concluída pelo agente {agente.nome} após {agente.actions_successful_for_objective} ações bem-sucedidas.")
                    registrar_evento(f"Tarefa '{task_to_complete.description}' (ID: {task_id_from_obj}) marcada como 'done' pelo agente {agente.nome}.")
                    logger.info(f"Tarefa '{task_to_complete.description}' (ID: {task_id_from_obj}) COMPLETADA por {agente.nome}.")
                    agente.objetivo_atual = "Aguardando novas atribuições."
                    agente.actions_successful_for_objective = 0
                    logger.info(f"Objetivo do agente {agente.nome} resetado. Actions successful resetado.")
                elif task_to_complete and task_to_complete.status != "in_progress":
                    logger.warning(f"Agente {agente.nome} tentou completar tarefa '{task_to_complete.description}' (ID: {task_id_from_obj}) mas seu status é '{task_to_complete.status}', não 'in_progress'.")
                    if task_to_complete.status == "done": # Se a tarefa já foi marcada como done por outro meio
                        agente.objetivo_atual = "Aguardando novas atribuições."
                        agente.actions_successful_for_objective = 0
                elif not task_to_complete:
                    logger.error(f"Agente {agente.nome} tentou completar tarefa ID '{task_id_from_obj}' mas a tarefa não foi encontrada em tarefas_pendentes.")
                    agente.objetivo_atual = "Erro: Tarefa do objetivo não encontrada."
                    agente.actions_successful_for_objective = 0
            except IndexError:
                logger.error(f"Erro ao parsear task_id do objetivo '{agente.objetivo_atual}' do agente {agente.nome}.")
                agente.objetivo_atual = "Erro: Formato de objetivo de tarefa inválido."
                agente.actions_successful_for_objective = 0
            except Exception as e:
                logger.error(f"Erro inesperado ao processar conclusão de tarefa para agente {agente.nome}: {e}", exc_info=True)
                agente.objetivo_atual = "Erro ao processar conclusão de tarefa."
                agente.actions_successful_for_objective = 0


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
# Import sys for KeyboardInterrupt and sys.exit
import sys
# random and time are already imported. ciclo_criativo as cc is also imported.
from rh import modulo_rh # Ensure rh module is imported

# Global variable to store current cycle number, might be useful for saving/resuming
ciclo_atual_simulacao: int = 0

def executar_um_ciclo_completo(ciclo_num: int) -> bool:
    """
    Executa todas as operações lógicas para um único ciclo da simulação.
    Retorna True se o ciclo completou normalmente, False em caso de erro crítico.
    """
    global ciclo_atual_simulacao
    ciclo_atual_simulacao = ciclo_num # Update global cycle counter

    logger.info(f"--- Iniciando Ciclo {ciclo_num} ---")
    try:
        # Gerar tarefas automáticas se não houver pendentes (lógica do loop antigo)
        if not tarefas_pendentes:
            if MODO_VIDA_INFINITA:
                novas_tarefas_desc = [
                    "Expandir para novo mercado internacional VI",
                    "Desenvolver funcionalidade revolucionária X VI",
                    "Criar campanha de marketing viral VI",
                    "Otimizar infraestrutura para escala global VI",
                    "Pesquisar aquisição de startup promissora VI"
                ]
                registrar_evento(f"VIDA INFINITA: Gerando {len(novas_tarefas_desc)} tarefas automáticas.")
            else:
                novas_tarefas_desc = [
                    "Pesquisar novas tecnologias disruptivas",
                    "Analisar feedback de clientes e propor melhorias"
                ]
                registrar_evento(f"Gerando {len(novas_tarefas_desc)} tarefas automáticas padrão.")
            for desc_tarefa in novas_tarefas_desc:
                adicionar_tarefa(desc_tarefa) # adicionar_tarefa já registra evento

        # Módulo de RH verifica e contrata se necessário
        modulo_rh.verificar()

        # Ciclo criativo (ideias, validação, prototipagem de produtos)
        cc.executar_ciclo_criativo()

        # Execução de serviços validados (atribuição, progresso, conclusão)
        cc.executar_servicos_validados() # Esta função foi criada na Subtask 5

        # Lógica de decisão e ação dos agentes via LLM
        # Selecionar um subconjunto de agentes para processamento LLM neste ciclo
        todos_os_agentes = list(agentes.values())
        random.shuffle(todos_os_agentes) # Embaralhar para dar chance a todos ao longo do tempo

        # Ajustar MAX_LLM_AGENTS_PER_CYCLE em modo vida infinita para acelerar ou manter como está
        max_agents_this_cycle = MAX_LLM_AGENTS_PER_CYCLE
        if MODO_VIDA_INFINITA and MAX_LLM_AGENTS_PER_CYCLE <= 5: # Exemplo: aumentar um pouco em VI se for baixo
             max_agents_this_cycle = min(len(todos_os_agentes), 10) # Processar mais, até 10 ou todos se menos de 10

        agentes_para_llm = todos_os_agentes[:max_agents_this_cycle]

        logger.info(
            f"Selecionados {len(agentes_para_llm)} de {len(todos_os_agentes)} agentes "
            f"para processamento LLM neste ciclo (limite configurado: {MAX_LLM_AGENTS_PER_CYCLE}, neste ciclo: {max_agents_this_cycle})."
        )

        for agente in agentes_para_llm:
            if agente.funcao.lower() == "executor" and agente.objetivo_atual.startswith("task_id:"):
                 # Se o executor já tem uma tarefa específica, seu prompt de decisão pode ser diferente
                 # ou ele pode pular a fase de decisão genérica e focar na execução da tarefa.
                 # Por agora, vamos permitir que ele tome decisões (ficar, mover, mensagem)
                 # e o progresso da tarefa é contado por ações bem-sucedidas.
                 pass # Continua para o prompt de decisão normal

            prompt = gerar_prompt_decisao(agente)
            resposta = enviar_para_llm(agente, prompt)
            executar_resposta(agente, resposta)

        # Calcular lucro/custos do ciclo
        info_lucro = calcular_lucro_ciclo()
        logger.info(f"Saldo após ciclo {ciclo_num}: {info_lucro['saldo']:.2f}. Receita ciclo: {info_lucro['receita_total_ciclo']:.2f}, Custos ciclo: {info_lucro['custos']:.2f}.")
        logger.info(f"--- Fim do Ciclo {ciclo_num} ---")
        return True
    except Exception as e:
        logger.error(f"Erro crítico durante o ciclo {ciclo_num}: {e}", exc_info=True)
        registrar_evento(f"ERRO CRÍTICO no ciclo {ciclo_num}: {e}")
        return False


def run_simulation_entry_point(num_cycles: int, resume_flag: bool):
    """
    Ponto de entrada principal para executar a simulação.
    Controla a inicialização, o loop de ciclos e o encerramento.
    """
    global MODO_VIDA_INFINITA, ciclo_atual_simulacao

    # Definir nomes de arquivos padrão para salvar/carregar
    save_file_agentes = "agentes_estado.json"
    save_file_locais = "locais_estado.json"
    save_file_ideias = "historico_ideias.json"
    save_file_servicos = "servicos.json"
    save_file_saldo = "saldo.json"
    save_file_tarefas = "tarefas.json"
    save_file_eventos = "eventos.json"

    if resume_flag:
        try:
            logger.info("Tentando retomar simulação do estado salvo...")
            carregar_dados(
                save_file_agentes, save_file_locais, save_file_ideias,
                save_file_servicos, save_file_saldo, save_file_tarefas, save_file_eventos
            )
            logger.info("Dados da simulação anterior carregados com sucesso.")
            # Aqui, poderíamos carregar `ciclo_atual_simulacao` se o salvássemos.
            # Por enquanto, se resume, os ciclos recomeçam a contagem do loop,
            # mas o estado da empresa (saldo, tarefas, etc.) é contínuo.
        except FileNotFoundError: # Genérico, pois carregar_dados lida com arquivos individuais
            logger.warning("Um ou mais arquivos de save não foram encontrados. Iniciando nova simulação.")
            inicializar_automaticamente()
            ciclo_atual_simulacao = 0
        except Exception as e:
            logger.error(f"Erro ao carregar dados: {e}. Iniciando nova simulação.", exc_info=True)
            inicializar_automaticamente()
            ciclo_atual_simulacao = 0
    else:
        logger.info("Iniciando nova simulação.")
        inicializar_automaticamente()
        ciclo_atual_simulacao = 0

    if num_cycles <= 0:
        definir_modo_vida_infinita(True) # Isso também loga e registra evento
        logger.info("Modo Vida Infinita ativado. Executando até Ctrl-C.")
    else:
        definir_modo_vida_infinita(False)
        logger.info(f"Executando por {num_cycles} ciclos.")

    try:
        if MODO_VIDA_INFINITA:
            # Se ciclo_atual_simulacao foi carregado, continuar dele. Senão, começar do 1.
            loop_start_cycle = ciclo_atual_simulacao + 1 if ciclo_atual_simulacao > 0 and resume_flag else 1

            current_loop_cycle = loop_start_cycle -1 # Ajuste para que o primeiro ciclo seja o 'loop_start_cycle'
            while True:
                current_loop_cycle +=1
                if not executar_um_ciclo_completo(current_loop_cycle):
                    logger.error(f"Encerrando simulação devido a erro crítico no ciclo {current_loop_cycle}.")
                    break
        else: # Finite cycles
            start_cycle_num = ciclo_atual_simulacao + 1 if ciclo_atual_simulacao > 0 and resume_flag else 1
            end_cycle_num = start_cycle_num + num_cycles -1

            for i in range(start_cycle_num, end_cycle_num + 1):
                if not executar_um_ciclo_completo(i):
                    logger.error(f"Encerrando simulação devido a erro crítico no ciclo {i}.")
                    break

    except KeyboardInterrupt:
        logger.info("\nCtrl-C detectado pelo usuário. Finalizando simulação...")
        # O bloco finally cuidará do salvamento.
    except Exception as e:
        logger.critical(f"Erro não tratado no loop principal da simulação: {e}", exc_info=True)
        # O bloco finally cuidará do salvamento.
    finally:
        logger.info("Salvando estado final da simulação...")
        try:
            # Aqui, poderíamos salvar `ciclo_atual_simulacao` também, talvez em saldo.json ou um meta_estado.json
            salvar_dados(
                save_file_agentes, save_file_locais, save_file_ideias,
                save_file_servicos, save_file_saldo, save_file_tarefas, save_file_eventos
            )
            logger.info("Estado da simulação salvo com sucesso.")
        except Exception as e_save:
            logger.error(f"Erro crítico ao tentar salvar o estado final da simulação: {e_save}", exc_info=True)

        logger.info(f"Simulação finalizada no ciclo {ciclo_atual_simulacao}.")
        if MODO_VIDA_INFINITA:
             logger.info("Modo Vida Infinita estava ATIVADO.")
        sys.exit(0) # Garante que o programa saia após o finally, especialmente se houve exceção não pega antes.
