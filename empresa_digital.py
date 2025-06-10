# -*- coding: utf-8 -*-
"""Simulador de uma empresa digital impulsionada por Modelos de Linguagem (LLMs).

Este módulo define a estrutura central para simular uma empresa onde agentes,
representados como entidades de software, tomam decisões e interagem com base
em prompts processados por LLMs através da API OpenRouter.
Ele gerencia o estado da empresa, incluindo agentes, locais, finanças e
o fluxo de eventos e decisões.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import json
import logging
import requests # Adicionado para chamadas HTTP
# import json # Já importado acima
# import logging # Já importado acima
from api import obter_api_key # Adicionado para obter a chave da API

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
        a decisão do agente) ou uma string JSON de erro em caso de falha na
        chamada da API ou processamento da resposta.

    Raises:
        Não lança exceções diretamente, mas retorna strings JSON de erro
        em casos como falha na API, chave não encontrada, timeout, ou
        estrutura de resposta inesperada. Erros são logados.
    """
    logging.debug(f"Iniciando chamada para OpenRouter API para o agente {agente.nome} com modelo {agente.modelo_llm}.")
    logging.debug(f"Prompt enviado para OpenRouter (modelo {agente.modelo_llm}):\n{prompt}")

    try:
        api_key = obter_api_key()
        if not api_key:
            logging.error("OPENROUTER_API_KEY não configurada.") # Mensagem mais clara
            return json.dumps({"error": "API key not found", "details": "OpenRouter API key is missing or not configured."})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": agente.modelo_llm,
            "messages": [{"role": "user", "content": prompt}],
        }

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        logging.debug(f"Resposta crua da OpenRouter (status {response.status_code}): {response.text}")
        response.raise_for_status()

        response_data = response.json()

        # Extrai o conteúdo da mensagem do LLM
        # Adicionado tratamento defensivo para diferentes estruturas de resposta
        if response_data.get("choices") and \
           isinstance(response_data["choices"], list) and \
           len(response_data["choices"]) > 0 and \
           response_data["choices"][0].get("message") and \
           isinstance(response_data["choices"][0]["message"], dict) and \
           response_data["choices"][0]["message"].get("content"):
            content = response_data['choices'][0]['message']['content']
            return content
        else:
            logging.error("Estrutura de resposta da API OpenRouter inesperada: %s", response_data) # Mantido logging.error
            return json.dumps({"error": "Invalid response structure", "details": "Unexpected API response format."})

    except requests.exceptions.Timeout as e:
        logging.error("Timeout durante a chamada para a API OpenRouter para o agente %s: %s", agente.nome, e) # Usar logging.error e incluir nome do agente
        return json.dumps({"error": "API call failed", "details": "Request timed out."})
    except requests.exceptions.RequestException as e:
        logging.error("Erro na chamada para a API OpenRouter para o agente %s: %s", agente.nome, e) # Usar logging.error e incluir nome do agente
        return json.dumps({"error": "API call failed", "details": str(e)})
    except json.JSONDecodeError as e: # Especificar JSONDecodeError para parsing da resposta da API
        logging.error("Erro ao decodificar JSON da resposta da API OpenRouter para o agente %s: %s. Resposta: %s", agente.nome, e, response.text if 'response' in locals() else "N/A")
        return json.dumps({"error": "API call failed", "details": "Invalid JSON response from API."})
    except (KeyError, IndexError, TypeError) as e:
        logging.error("Erro ao processar estrutura da resposta da API OpenRouter para o agente %s: %s", agente.nome, e) # Usar logging.error e incluir nome do agente
        return json.dumps({"error": "Invalid response structure", "details": str(e)})


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
            msg = f"Tentativa de mover {agente.nome} para destino inválido (ausente ou formato incorreto): '{destino}'."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(f"mover para '{destino}' -> falha (destino invalido)", False)

            msg_ficar_fallback_mover = f"{agente.nome} permanece em {agente.local_atual.nome} (fallback de 'mover' por destino inválido)."
            registrar_evento(msg_ficar_fallback_mover)
            logging.info(msg_ficar_fallback_mover)
            agente.registrar_acao("ficar (fallback mover) -> ok", True)
        elif destino not in locais:
            msg = f"Destino '{destino}' não encontrado para {agente.nome}."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(f"mover para '{destino}' -> falha (local nao existe)", False)

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
            agente.registrar_acao(f"mensagem para '{destinatario}' -> falha (dados invalidos)", False)

            msg_ficar_fallback_msg = f"{agente.nome} permanece em {agente.local_atual.nome} (fallback de 'mensagem' por dados inválidos)."
            registrar_evento(msg_ficar_fallback_msg)
            logging.info(msg_ficar_fallback_msg)
            agente.registrar_acao("ficar (fallback mensagem) -> ok", True)
        elif destinatario not in agentes:
            msg = f"Destinatário '{destinatario}' da mensagem de {agente.nome} não encontrado."
            registrar_evento(msg)
            logging.warning(f"{msg} Aplicando fallback: 'ficar'.")
            agente.registrar_acao(f"mensagem para '{destinatario}' -> falha (destinatario nao existe)", False)

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
    from ciclo_criativo import executar_ciclo_criativo

    inicializar_automaticamente()

    for ciclo in range(1, 4):
        logging.info("=== Ciclo %d ===", ciclo)
        modulo_rh.verificar()
        executar_ciclo_criativo()
        for agente in list(agentes.values()):
            prompt = gerar_prompt_decisao(agente)
            resposta = enviar_para_llm(agente, prompt)
            executar_resposta(agente, resposta)
        info = calcular_lucro_ciclo()
        logging.info("Saldo apos ciclo %d: %.2f", ciclo, info["saldo"])

