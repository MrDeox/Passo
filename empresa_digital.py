# -*- coding: utf-8 -*-
"""Esqueleto de um sistema para simular uma empresa digital.

Este módulo define classes e funções básicas para representar agentes
(equivalentes a funcionários ou bots) e locais da empresa.

O objetivo é ter um ponto de partida para criação de interações mais
complexas no futuro.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json

# Lista global de tarefas pendentes que podem ser atribuídas a novos agentes
tarefas_pendentes: List[str] = []

# Dicionários globais para armazenar os agentes e os locais cadastrados.
agentes: Dict[str, "Agente"] = {}
locais: Dict[str, "Local"] = {}


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
    """Representa um agente da empresa."""

    nome: str
    funcao: str
    modelo_llm: str
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


def salvar_dados(arquivo_agentes: str, arquivo_locais: str) -> None:
    """Salva os dicionários globais de agentes e locais em arquivos JSON.

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


def carregar_dados(arquivo_agentes: str, arquivo_locais: str) -> None:
    """Carrega arquivos JSON recriando os dicionários de agentes e locais."""

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
                f"Feedback do CEO: {agente.feedback_ceo or 'Nenhum'}",
                f"Estado emocional: {agente.estado_emocional}",
            ]
        )

    instrucoes = (
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


def enviar_para_llm(agente: Agente, prompt: str) -> str:
    """Simula o envio do prompt para o modelo LLM do agente.

    No lugar da chamada real à API, apenas imprime o prompt e retorna uma
    string fixa representando a resposta da IA. Em um cenário real, esta
    função faria a requisição de rede ao provedor de LLM configurado.
    """

    print(f"\n--- Prompt enviado para {agente.modelo_llm} ({agente.nome}) ---")
    print(prompt)
    print("--- Fim do prompt ---\n")

    # Resposta simulada apenas para fins de demonstração.
    respostas_simuladas = {
        "Alice": '{"acao": "mover", "local": "Sala de Reunião"}',
        "Bob": '{"acao": "mensagem", "destinatario": "Carol", "texto": "Preciso de ajuda"}',
        "Carol": '{"acao": "ficar"}',
    }
    return respostas_simuladas.get(agente.nome, '{"acao": "ficar"}')


def executar_resposta(agente: Agente, resposta: str) -> None:
    """Executa a ação retornada pelo LLM para o agente."""

    try:
        dados = json.loads(resposta)
    except json.JSONDecodeError:
        print(f"Resposta inválida para {agente.nome}: {resposta}")
        return

    acao = dados.get("acao")

    if acao == "ficar":
        print(f"{agente.nome} permanece em {agente.local_atual.nome}.")
        agente.registrar_acao("ficar -> ok", True)
    elif acao == "mover":
        destino = dados.get("local")
        if destino and destino in locais:
            mover_agente(agente.nome, destino)
            print(f"{agente.nome} moveu-se para {destino}.")
            agente.registrar_acao(f"mover para {destino} -> ok", True)
        else:
            print(f"Destino invalido para {agente.nome}: {destino}")
            agente.registrar_acao(f"mover para {destino} -> falha", False)
    elif acao == "mensagem":
        dest = dados.get("destinatario")
        texto = dados.get("texto", "")
        print(f"{agente.nome} envia mensagem para {dest}: {texto}")
        agente.historico_interacoes.append(f"para {dest}: {texto}")
        if len(agente.historico_interacoes) > 3:
            agente.historico_interacoes = agente.historico_interacoes[-3:]
        agente.registrar_acao(f"mensagem para {dest}", True)
    else:
        print(f"Acao desconhecida para {agente.nome}: {acao}")
        agente.registrar_acao(f"acao desconhecida: {acao}", False)


# ---------------------------------------------------------------------------
# Exemplo de uso
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Criar dois locais
    sala_reuniao = criar_local(
        "Sala de Reunião",
        "Espaço para realizar reuniões",
        ["mesa", "projetor"],
    )
    sala_tecnologia = criar_local(
        "Sala de Tecnologia",
        "Laboratório de desenvolvimento",
        ["computadores", "ferramentas de rede"],
    )

    # Criar três agentes
    alice = criar_agente(
        "Alice",
        "Gerente",
        "gpt-3.5-turbo",
        "Sala de Reunião",
        objetivo="Planejar projeto X",
    )
    bob = criar_agente(
        "Bob",
        "Desenvolvedor",
        "deepseek-chat",
        "Sala de Tecnologia",
        objetivo="Implementar tarefa Y",
    )
    carol = criar_agente(
        "Carol",
        "Analista",
        "gpt-3.5-turbo",
        "Sala de Reunião",
        objetivo="Coletar requisitos",
    )

    # Mover um agente entre salas
    mover_agente("Alice", "Sala de Tecnologia")

    # Exibir situação atual com prompts dinâmicos
    for agente in agentes.values():
        print("\n" + gerar_prompt_dinamico(agente))

    # Persistir o estado em disco
    salvar_dados("agentes.json", "locais.json")

    # Limpar registros e recarregar do disco para demonstrar a função
    agentes.clear()
    locais.clear()
    carregar_dados("agentes.json", "locais.json")

    print("\nEstado restaurado do disco:")
    for agente in agentes.values():
        print(f"- {agente.nome} está em {agente.local_atual.nome}")

    # Demonstrar várias iterações de decisões para evidenciar a evolução do
    # histórico e do prompt adaptativo
    from rh import modulo_rh

    for ciclo in range(1, 4):
        print(f"\n=== Ciclo {ciclo} ===")
        modulo_rh.verificar()
        for agente in list(agentes.values()):
            prompt = gerar_prompt_decisao(agente)
            resposta = enviar_para_llm(agente, prompt)
            executar_resposta(agente, resposta)
