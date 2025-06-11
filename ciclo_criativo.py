import logging
from dataclasses import asdict # dataclass is now in core_types
from typing import List, Dict, Optional
import json # Added for saving/loading historico_ideias
import time # For timestamps in Service history
import uuid # For Service IDs
import os # For marketing content persistence

import config # Added
import state # Added
# import empresa_digital # Keep for NOME_EMPRESA, if it's used and defined there. Otherwise, remove.
# For now, assuming NOME_EMPRESA is still expected from empresa_digital or will be handled.
import empresa_digital
from agent_utils import selecionar_modelo, criar_agente, gerar_prompt_dinamico, enviar_para_llm # Added

from .core_types import Ideia, Service # Import Ideia and Service from core_types
# criador_de_produtos and divulgador imports were relative, ensure they are absolute now if needed.
# They were changed to absolute in a previous subtask.
from .criador_de_produtos import produto_digital
from divulgador import sugerir_conteudo_marketing

logger = logging.getLogger(__name__)

# Ideia dataclass definition is removed from here

# historico_ideias: List[Ideia] = [] # Moved to state.py
# historico_servicos: List[Service] = [] # Moved to state.py
# preferencia_temas: Dict[str, int] = {} # Moved to state.py


def salvar_historico_ideias(filename="historico_ideias.json"):
    """Salva o state.historico_ideias em um arquivo JSON."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # Convert Ideia objects to dictionaries for JSON serialization
            json.dump([asdict(ideia) for ideia in state.historico_ideias], f, ensure_ascii=False, indent=4)
        logger.info(f"Histórico de ideias salvo em {filename}")
    except IOError as e:
        logger.error(f"Erro ao salvar histórico de ideias: {e}")

def carregar_historico_ideias(filename="historico_ideias.json") -> List[Ideia]:
    """Carrega o state.historico_ideias de um arquivo JSON."""
    # Removed global historico_ideias
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            ideias_data = json.load(f)
            # Convert dictionaries back to Ideia objects
            state.historico_ideias = [Ideia(**data) for data in ideias_data]
            logger.info(f"Histórico de ideias carregado de {filename}")
            return state.historico_ideias
    except FileNotFoundError:
        logger.warning(f"Arquivo de histórico de ideias '{filename}' não encontrado. Iniciando com histórico vazio.")
        state.historico_ideias = []
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do histórico de ideias: {e}. Iniciando com histórico vazio.")
        state.historico_ideias = []
        return []
    except Exception as e: # Catch other potential errors during loading (e.g., TypeError if Ideia structure changed)
        logger.error(f"Erro inesperado ao carregar histórico de ideias: {e}. Iniciando com histórico vazio.")
        state.historico_ideias = []
        return []


def salvar_historico_servicos(filename="servicos.json"):
    """Salva o state.historico_servicos em um arquivo JSON."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(servico) for servico in state.historico_servicos], f, ensure_ascii=False, indent=4)
        logger.info(f"Histórico de serviços salvo em {filename}")
    except IOError as e:
        logger.error(f"Erro ao salvar histórico de serviços: {e}")

def carregar_historico_servicos(filename="servicos.json") -> List[Service]:
    """Carrega o state.historico_servicos de um arquivo JSON."""
    # Removed global historico_servicos
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            servicos_data = json.load(f)
            # Convert dictionaries back to Service objects
            # Handle potential missing fields if the Service class evolves
            loaded_services = []
            for data in servicos_data:
                # Ensure all fields required by Service.__init__ are present or provide defaults
                # This is a basic way to handle it; more robust migration might be needed for big changes
                data.setdefault('id', uuid.uuid4().hex)
                data.setdefault('service_name', 'Nome do Serviço Padrão')
                data.setdefault('description', 'Descrição Padrão')
                data.setdefault('author', 'Autor Desconhecido')
                data.setdefault('required_skills', [])
                data.setdefault('estimated_effort_hours', 0)
                data.setdefault('pricing_model', 'fixed_price')
                data.setdefault('price_amount', 0.0)
                data.setdefault('status', 'proposed')
                data.setdefault('history', [])
                data.setdefault('creation_timestamp', time.time())
                data.setdefault('validation_timestamp', None)
                data.setdefault('completion_timestamp', None)
                # Add defaults for new fields from the current subtask
                data.setdefault('assigned_agent_name', None)
                data.setdefault('delivery_start_timestamp', None)
                data.setdefault('revenue_calculated', False) # Default for new field
                loaded_services.append(Service(**data))
            state.historico_servicos = loaded_services
            logger.info(f"Histórico de serviços carregado de {filename}. {len(state.historico_servicos)} serviços carregados.")
            return state.historico_servicos
    except FileNotFoundError:
        logger.warning(f"Arquivo de histórico de serviços '{filename}' não encontrado. Iniciando com histórico vazio.")
        state.historico_servicos = []
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do histórico de serviços: {e}. Iniciando com histórico vazio.")
        state.historico_servicos = []
        return []
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar histórico de serviços: {e}. Iniciando com histórico vazio.")
        state.historico_servicos = []
        return []


def _tema_preferido() -> str:
    """Define o tema a ser priorizado conforme resultados anteriores."""
    if not state.preferencia_temas:
        return "IA"
    return max(state.preferencia_temas, key=state.preferencia_temas.get)


def propor_ideias() -> None: # Modified to not return, but add directly to historicos
    """
    Gera ideias de produtos ou serviços usando LLM a partir de agentes com funcao 'Ideacao'.
    O LLM decide se quer propor um produto, um serviço, ou nada.
    As ideias/serviços aprovados são adicionados diretamente ao histórico correspondente.
    """
    agentes_ideacao = [ag for ag in state.agentes.values() if ag.funcao.lower() == "ideacao"]
    if not agentes_ideacao:
        logger.info("Nenhum agente de 'Ideacao' encontrado para propor ideias/serviços.")
        return

    tema_preferido = _tema_preferido() # Usado no prompt

    for agente in agentes_ideacao:
        contexto_agente = gerar_prompt_dinamico(agente) # Use from agent_utils
        prompt_ideia_ou_servico = f"""{contexto_agente}
Você é um agente de ideação. Sua tarefa é propor uma nova ideia de PRODUTO, um novo SERVIÇO para a empresa, ou decidir que nenhuma ideia é adequada no momento.
Considere o tema preferido atual da empresa: '{tema_preferido}'. Você pode seguir este tema ou propor algo inovador.

Responda APENAS com um JSON no seguinte formato:

Se for uma ideia de PRODUTO:
{{
  "type": "product",
  "name": "Nome do Produto",
  "description": "Descrição detalhada do produto e seu público-alvo.",
  "justification": "Justificativa para o produto, por que ele seria valioso.",
  "target_audience": "Público-alvo específico para este produto."
}}

Se for uma ideia de SERVIÇO:
{{
  "type": "service",
  "service_name": "Nome do Serviço",
  "description": "Descrição detalhada do serviço e o que ele entrega.",
  "required_skills": ["Habilidade1", "Habilidade2", "FuncaoAgenteRelevante"],
  "estimated_effort_hours": 50,
  "pricing_model": "fixed_price", // ou "hourly_rate"
  "price_amount": 2500.00 // Preço total ou taxa horária
}}

Se NENHUMA ideia for proposta:
{{
  "type": "none"
}}

Responda APENAS com o JSON.
"""
        logger.debug(f"Prompt de proposta de ideia/serviço para {agente.nome}:\n{prompt_ideia_ou_servico}")
        resposta_llm_raw = enviar_para_llm(agente, prompt_ideia_ou_servico) # Use from agent_utils

        try:
            resposta_json = json.loads(resposta_llm_raw)
            idea_type = resposta_json.get("type")

            if idea_type == "product":
                nova_ideia = Ideia(
                    descricao=resposta_json.get("description", "Produto sem descrição detalhada."),
                    justificativa=resposta_json.get("justification", "Sem justificativa fornecida."),
                    autor=agente.nome,
                    # Campos adicionais podem ser adicionados aqui se Ideia for expandida
                    # ex: nome=resposta_json.get("name"), publico_alvo=resposta_json.get("target_audience")
                )
                # Poderíamos adicionar o nome e target_audience à Ideia se a classe suportar
                # Por agora, a descrição e justificativa são os campos principais.
                if hasattr(nova_ideia, 'nome'): # Exemplo de como poderia ser se Ideia tivesse 'nome'
                    nova_ideia.nome = resposta_json.get("name", "Produto Sem Nome")

                if nova_ideia not in state.historico_ideias:
                    state.historico_ideias.append(nova_ideia)
                    logger.info(f"Nova IDEIA DE PRODUTO proposta por {agente.nome}: '{resposta_json.get('name', nova_ideia.descricao)}'")
                    state.registrar_evento(f"Nova IDEIA DE PRODUTO: '{resposta_json.get('name', nova_ideia.descricao)}' por {agente.nome}")
                else:
                    logger.info(f"Ideia de produto similar já existe no histórico, proposta por {agente.nome}: '{resposta_json.get('name', nova_ideia.descricao)}'")

            elif idea_type == "service":
                novo_servico = Service(
                    service_name=resposta_json.get("service_name", "Serviço Sem Nome"),
                    description=resposta_json.get("description", "Sem descrição detalhada."),
                    author=agente.nome,
                    required_skills=resposta_json.get("required_skills", []),
                    estimated_effort_hours=resposta_json.get("estimated_effort_hours", 0),
                    pricing_model=resposta_json.get("pricing_model", "fixed_price"),
                    price_amount=resposta_json.get("price_amount", 0.0),
                )
                if novo_servico not in state.historico_servicos:
                    state.historico_servicos.append(novo_servico)
                    logger.info(f"Novo SERVIÇO proposto por {agente.nome}: '{novo_servico.service_name}' (ID: {novo_servico.id})")
                    state.registrar_evento(f"Novo SERVIÇO proposto: '{novo_servico.service_name}' por {agente.nome}")
                else:
                    logger.info(f"Serviço similar já existe no histórico, proposto por {agente.nome}: '{novo_servico.service_name}'")

            elif idea_type == "none":
                logger.info(f"Agente {agente.nome} decidiu não propor uma ideia ou serviço desta vez.")
            else:
                logger.warning(f"Resposta LLM para proposta de {agente.nome} não reconhecida ou tipo incorreto: {resposta_llm_raw}")

        except json.JSONDecodeError:
            logger.error(f"Falha ao decodificar JSON da resposta LLM para proposta de {agente.nome}: {resposta_llm_raw}")
        except Exception as e:
            logger.error(f"Erro ao processar proposta de {agente.nome}: {e}. Resposta LLM: {resposta_llm_raw}", exc_info=True)

# A função propor_servicos() foi removida pois sua funcionalidade foi integrada em propor_ideias().

from typing import Union # For type hinting Ideia | Service

def _aplicar_heuristica_fallback(item: Union[Ideia, Service]) -> None:
    """Aplica uma heurística de fallback para validar ou rejeitar um item."""
    item_type = "Ideia de Produto" if isinstance(item, Ideia) else "Serviço"
    item_name = item.descricao if isinstance(item, Ideia) else item.service_name

    logger.info(f"Aplicando heurística de fallback para {item_type}: '{item_name}'.")

    if isinstance(item, Ideia):
        # Lógica de fallback original para Ideias (ex: baseada em keyword)
        aprovado_fallback = "ia" in item.descricao.lower() or "produto" in item.descricao.lower()
        item.validada = aprovado_fallback
        status_msg = "aprovada (fallback)" if aprovado_fallback else "rejeitada (fallback)"
        logger.info(f"Fallback: {item_type} '{item_name}' foi {status_msg} pela heurística.")
        state.registrar_evento(f"Fallback: {item_type} '{item_name}' {status_msg}.")
    elif isinstance(item, Service):
        # Lógica de fallback para Serviços (pode ser mais simples ou complexa)
        # Exemplo: aprovar serviços com baixo esforço estimado ou rejeitar outros.
        if item.estimated_effort_hours <= 20 and item.price_amount > 0:
            item.update_status("validated", "Validado por heurística de fallback (baixo esforço).")
            logger.info(f"Fallback: Serviço '{item_name}' APROVADO (baixo esforço).")
            state.registrar_evento(f"Fallback: Serviço '{item_name}' APROVADO (baixo esforço).")
        else:
            item.update_status("rejected", "Rejeitado por heurística de fallback (critério não atendido).")
            logger.info(f"Fallback: Serviço '{item_name}' REJEITADO (critério não atendido).")
            state.registrar_evento(f"Fallback: Serviço '{item_name}' REJEITADO (critério não atendido).")

def _validar_item_com_llm(item: Union[Ideia, Service], validador: empresa_digital.Agente) -> bool:
    """
    Valida um item (Ideia ou Service) usando o LLM de um agente Validador.
    Implementa um loop de retentativa para erros de parsing JSON.
    Retorna True se a validação foi concluída (aprovada, rejeitada ou auto-rejeitada),
    False se houve falha persistente de comunicação com LLM (não JSON).
    """
    MAX_VALIDATION_ATTEMPTS = 3
    validation_attempts = 0
    item_type_str = "Ideia de Produto" if isinstance(item, Ideia) else "Serviço"
    item_identifier = item.descricao if isinstance(item, Ideia) else item.service_name

    prompt_context = f"Você é um agente Validador da empresa '{config.NOME_EMPRESA}'. Sua tarefa é analisar a seguinte proposta e decidir se deve ser 'aprovar' ou 'rejeitar'."
    habilidades_disponiveis_simples = list(set(ag.funcao for ag in state.agentes.values())) # Para contexto do LLM

    if isinstance(item, Ideia):
        prompt_details = f"""
Tipo da Proposta: {item_type_str}
Nome/Descrição: {item.descricao}
Justificativa: {item.justificativa}
Autor: {item.autor}
"""
    else: # Service
        prompt_details = f"""
Tipo da Proposta: {item_type_str}
ID: {item.id}
Nome: {item.service_name}
Descrição: {item.description}
Autor: {item.author}
Habilidades Requeridas: {', '.join(item.required_skills)}
Esforço Estimado (horas): {item.estimated_effort_hours}
Modelo de Preço: {item.pricing_model}
Valor/Taxa: {item.price_amount}
Habilidades/Funções de agentes disponíveis na empresa (simplificado): {', '.join(habilidades_disponiveis_simples)}.
"""

    prompt_llm = f"""{gerar_prompt_dinamico(validador)}
{prompt_context}
{prompt_details}
Analise a proposta acima. Considere sua viabilidade, alinhamento estratégico, potencial de valor e riscos.
Responda APENAS com um JSON contendo sua decisão e uma breve justificativa:
{{
  "decision": "aprovar", // ou "rejeitar"
  "justification": "Sua justificativa detalhada aqui (seja conciso)."
}}
"""
    logger.debug(f"Prompt de validação para {item_type_str} '{item_identifier}' (Validador: {validador.nome}):\n{prompt_llm}")

    while validation_attempts < MAX_VALIDATION_ATTEMPTS:
        validation_attempts += 1
        logger.info(f"Tentativa de validação {validation_attempts}/{MAX_VALIDATION_ATTEMPTS} para {item_type_str} '{item_identifier}' com {validador.nome}.")

        try:
            resposta_llm_raw = enviar_para_llm(validador, prompt_llm) # Use from agent_utils
            if not resposta_llm_raw: # Caso o LLM retorne string vazia ou None
                logger.error(f"Resposta LLM vazia na tentativa {validation_attempts} para {item_type_str} '{item_identifier}'.")
                if validation_attempts == MAX_VALIDATION_ATTEMPTS:
                    break # Sai para auto-rejeição por falha de LLM
                continue # Próxima tentativa

            resposta_json = json.loads(resposta_llm_raw)
            decisao = resposta_json.get("decision")
            justificativa = resposta_json.get("justification", "Sem justificativa fornecida pelo LLM.")

            if decisao == "aprovar":
                if isinstance(item, Ideia):
                    item.validada = True
                else: # Service
                    item.update_status("validated", f"Aprovado por {validador.nome}: {justificativa}")
                logger.info(f"{item_type_str} '{item_identifier}' APROVADO por {validador.nome} (Tentativa {validation_attempts}). Justificativa: {justificativa}")
                state.registrar_evento(f"{item_type_str} '{item_identifier}' APROVADO. Validador: {validador.nome}. Just.: {justificativa}")
                return True # Validação concluída
            elif decisao == "rejeitar":
                if isinstance(item, Ideia):
                    item.validada = False # Mantém False, mas registra o evento
                else: # Service
                    item.update_status("rejected", f"Rejeitado por {validador.nome}: {justificativa}")
                logger.info(f"{item_type_str} '{item_identifier}' REJEITADO por {validador.nome} (Tentativa {validation_attempts}). Justificativa: {justificativa}")
                state.registrar_evento(f"REJEITADO: {item_type_str} '{item_identifier}'. Validador: {validador.nome}. Just.: {justificativa}")
                return True # Validação concluída
            else:
                logger.warning(f"Decisão LLM ('{decisao}') não reconhecida na tentativa {validation_attempts} para {item_type_str} '{item_identifier}'. Resposta: {resposta_llm_raw}")
                # Se for a última tentativa e a decisão for inválida, cai para a auto-rejeição abaixo.

        except json.JSONDecodeError:
            logger.error(f"Falha ao decodificar JSON da resposta LLM na tentativa {validation_attempts} para {item_type_str} '{item_identifier}'. Resposta: {resposta_llm_raw}")
            # Se for a última tentativa com JSON inválido, cai para a auto-rejeição abaixo.
        except Exception as e: # Outras exceções, como problemas de API não tratados em enviar_para_llm
            logger.error(f"Erro ao enviar para LLM ou processar resposta na tentativa {validation_attempts} para {item_type_str} '{item_identifier}': {e}", exc_info=True)
            if validation_attempts == MAX_VALIDATION_ATTEMPTS: # Se falha de comunicação persistir
                logger.error(f"Falha de comunicação persistente com LLM para {item_type_str} '{item_identifier}' após {MAX_VALIDATION_ATTEMPTS} tentativas.")
                # Neste caso, a função retornará False, indicando falha de comunicação.
                # A heurística de fallback pode ser aplicada em `validar_propostas`.
                return False

        if validation_attempts == MAX_VALIDATION_ATTEMPTS: # Se chegou aqui é porque as tentativas esgotaram com JSON inválido ou decisão não reconhecida
            logger.warning(f"Esgotadas {MAX_VALIDATION_ATTEMPTS} tentativas de validação LLM para {item_type_str} '{item_identifier}'. Auto-rejeitando.")
            just_auto_rejeicao = f"Auto-rejeitado após {MAX_VALIDATION_ATTEMPTS} tentativas de validação LLM resultarem em resposta inválida ou não conclusiva."
            if isinstance(item, Ideia):
                item.validada = False
            else: # Service
                item.update_status("rejected", just_auto_rejeicao)
            logger.info(f"{item_type_str} '{item_identifier}' AUTO-REJEITADO. Motivo: {just_auto_rejeicao}")
            state.registrar_evento(f"AUTO-REJEITADO: {item_type_str} '{item_identifier}'. Motivo: {just_auto_rejeicao}")
            return True # Validação concluída (com auto-rejeição)

    # Se o loop terminar sem retornar True (o que não deveria acontecer devido à auto-rejeição na última tentativa)
    # ou se uma falha de comunicação persistente ocorreu e retornou False.
    # Este log é mais para o caso de falha de comunicação onde retornamos False.
    if validation_attempts == MAX_VALIDATION_ATTEMPTS: # Chegou aqui se retornou False de dentro do loop
        logger.error(f"Validação LLM para {item_type_str} '{item_identifier}' falhou após {MAX_VALIDATION_ATTEMPTS} tentativas devido a problemas de comunicação ou erro inesperado não tratado como JSON.")
        return False

    return False # Segurança, não deveria ser atingido normalmente.


def validar_propostas(ideias_para_validar: List[Ideia], servicos_para_validar: List[Service]) -> None:
    """
    Valida uma lista de ideias e serviços usando agentes Validadores e LLM.
    Aplica heurística de fallback se validadores não estiverem disponíveis ou LLM falhar persistentemente.
    """
    validadores = [a for a in state.agentes.values() if a.funcao.lower() == "validador"]

    itens_a_processar: List[Union[Ideia, Service]] = []

    for ideia in ideias_para_validar:
        if not ideia.validada and not ideia.executada:
            itens_a_processar.append(ideia)
        else:
            logger.info(f"Ideia '{ideia.descricao}' já validada ou executada. Pulando.")

    for servico in servicos_para_validar:
        if servico.status == "proposed":
            itens_a_processar.append(servico)
        else:
            logger.info(f"Serviço '{servico.service_name}' (ID: {servico.id}) não está 'proposed' (status: {servico.status}). Pulando.")

    if not itens_a_processar:
        logger.info("Nenhuma ideia ou serviço novo para validar neste ciclo.")
        return

    if not validadores:
        logger.warning("Nenhum agente 'Validador' encontrado. Aplicando heurística de fallback para todos os itens pendentes.")
        for item in itens_a_processar:
            _aplicar_heuristica_fallback(item)
        return

    validador_escolhido = validadores[0] # Simplista: pega o primeiro validador. Poderia ser aleatório ou round-robin.
    logger.info(f"Usando validador: {validador_escolhido.nome} para as próximas validações.")

    for item in itens_a_processar:
        item_type_str = "Ideia de Produto" if isinstance(item, Ideia) else "Serviço"
        item_identifier = item.descricao if isinstance(item, Ideia) else item.service_name

        logger.info(f"Iniciando processo de validação para {item_type_str}: '{item_identifier}'.")

        # Tenta validar com LLM
        llm_validation_completed_or_failed_definitively = _validar_item_com_llm(item, validador_escolhido)

        if not llm_validation_completed_or_failed_definitively:
            # Isso significa que _validar_item_com_llm retornou False,
            # indicando falha persistente de comunicação com LLM, não um JSON inválido ou decisão.
            logger.warning(f"Validação LLM para {item_type_str} '{item_identifier}' falhou devido a problemas de comunicação persistentes. Aplicando heurística de fallback.")
            _aplicar_heuristica_fallback(item)
        # Se llm_validation_completed_or_failed_definitively for True, o item foi aprovado, rejeitado pelo LLM, ou auto-rejeitado.
        # Nesses casos, a decisão do LLM (ou auto-rejeição) é final e o fallback não é aplicado.

def prototipar_ideias(ideias: List[Ideia]) -> None:
    """Simula prototipagem gerando lucro ou prejuizo."""
    for ideia in ideias:
        if not ideia.validada:
            continue

        # Tentativa de criar produto digital se ainda não foi criado
        if ideia.link_produto is None:
            logger.info(f"Tentando criar produto digital para ideia validada: {ideia.descricao}")
            try:
                # state.agentes e state.locais são usados agora
                product_url = produto_digital(ideia, state.agentes, state.locais)
                if product_url:
                    ideia.link_produto = product_url
                    # Evento de criação de produto já é registrado em produto_digital.py
                    logger.info(f"Produto '{ideia.descricao}' criado com sucesso: {product_url}")

                    # >>> Integration of Divulgador <<<
                    logger.info(f"Tentando gerar sugestões de marketing para '{ideia.descricao}'...")
                    marketing_sugestoes = sugerir_conteudo_marketing(ideia, product_url) # This is from .divulgador
                    if marketing_sugestoes:
                        logger.info(f"Sugestões de marketing geradas para '{ideia.descricao}'.")

                        # Persist marketing content
                        # PRODUTOS_MARKETING_DIR definition removed, will be imported from config.py later
                        try:
                            # Using config.PRODUTOS_MARKETING_DIR
                            idea_marketing_path = os.path.join(config.PRODUTOS_MARKETING_DIR, ideia.slug)
                            os.makedirs(idea_marketing_path, exist_ok=True)

                            filepath = os.path.join(idea_marketing_path, "marketing.md")
                            with open(filepath, "w", encoding="utf-8") as f:
                                f.write(marketing_sugestoes)
                            logger.info(f"Conteúdo de marketing para '{ideia.descricao}' salvo em {filepath}")

                            # Append summary to historico_eventos
                            resumo_marketing = marketing_sugestoes[:150].replace('\n', ' ') + "..."
                            state.registrar_evento(f"Marketing para '{ideia.descricao}': {resumo_marketing} (Salvo em: {filepath})")

                        except IOError as e:
                            logger.error(f"Erro ao salvar conteúdo de marketing para '{ideia.descricao}' em {filepath}: {e}")
                        except Exception as e_general:
                             logger.error(f"Erro inesperado ao salvar marketing para '{ideia.descricao}': {e_general}", exc_info=True)
                    else:
                        logger.warning(f"Não foram geradas sugestões de marketing para '{ideia.descricao}'.")
                    # >>> End Integration of Divulgador <<<

                    # Atualiza resultado da ideia com base na criação do produto
                    # A lógica de bônus aqui é um exemplo e pode ser ajustada.
                    # Removemos o bônus anterior de "sucesso" genérico se o produto foi criado.
                    ideia.resultado = 50.0 # Base result for successful product creation
                    if "ia" in ideia.descricao.lower(): # Bônus adicional para produtos de IA
                        ideia.resultado += 25.0
                    if "produto" in ideia.descricao.lower(): # Bônus adicional se a palavra "produto" estiver na descrição
                        ideia.resultado += 10.0
                else:
                    logger.error(f"Falha ao criar produto digital para a ideia: {ideia.descricao}")
                    state.registrar_evento(f"Falha na criação do produto para ideia: {ideia.descricao}")
                    ideia.resultado = -15.0 # Penalidade maior se a criação do produto falhar
            except Exception as e:
                logger.error(f"Exceção ao tentar criar produto digital para '{ideia.descricao}': {e}", exc_info=True)
                state.registrar_evento(f"Exceção na criação do produto para ideia '{ideia.descricao}': {e}")
                ideia.resultado = -20.0 # Penalidade por exceção

        # Lógica de simulação de prototipagem/resultado (executada mesmo se o produto já existia ou falhou, mas com resultado já ajustado)
        if not ideia.executada:
            ideia.executada = True
            # Se o resultado não foi definido pela lógica de criação de produto (ex: ideia já tinha link_produto)
            # ou se queremos adicionar mais alguma lógica de resultado baseada em 'sucesso'
            if ideia.resultado == 0.0 and not ideia.link_produto : # Só aplica resultado padrão se não foi tocado pela criação de produto.
                # Se 'ideia.resultado' ainda for 0.0 aqui (e não houve tentativa de criação de produto),
                # podemos considerar que não houve sucesso claro ou aplicar uma lógica de prototipagem simples.
                # Por ora, vamos manter a lógica que o resultado é primariamente definido pela criação do produto.
                # Se nenhuma criação ocorreu e resultado é 0, ele permanecerá 0.
                logger.info(f"Ideia '{ideia.descricao}' não teve produto criado e resultado inicial é 0.0. Nenhuma alteração de resultado aqui.")


            # Creditar lucro/prejuízo ao saldo da empresa e registrar evento
            # Isso deve acontecer após a tentativa de criação do produto e definição do ideia.resultado.
            if ideia.resultado > 0:
                state.saldo += ideia.resultado
                logger.info(f"Lucro do produto '{ideia.descricao}' de +{ideia.resultado:.2f} creditado. Saldo atual: {state.saldo:.2f}")
                state.registrar_evento(f"Lucro produto '{ideia.descricao}' (+{ideia.resultado:.2f}). Saldo atual: {state.saldo:.2f}")
            elif ideia.resultado < 0:
                state.saldo += ideia.resultado # Adiciona o valor negativo (subtrai)
                logger.info(f"Prejuízo/Custo do produto '{ideia.descricao}' de {ideia.resultado:.2f} debitado. Saldo atual: {state.saldo:.2f}")
                state.registrar_evento(f"Prejuízo/Custo produto '{ideia.descricao}' ({ideia.resultado:.2f}). Saldo atual: {state.saldo:.2f}")
            else: # ideia.resultado == 0
                logger.info(f"Produto '{ideia.descricao}' não gerou lucro nem prejuízo no estágio de prototipagem/criação. Saldo atual: {state.saldo:.2f}")
                # Não registrar evento de lucro/prejuízo se for zero, mas o evento de prototipagem abaixo cobrirá.

            tema = "IA" if "ia" in ideia.descricao.lower() else "outros" # TODO: Melhorar extração de tema
            # Correção do bug: usar ideia.resultado > 0 para determinar o sucesso para preferencia_temas.
            # Esta variável 'sucesso_da_ideia' é especificamente para a lógica de preferencia_temas.
            sucesso_para_preferencia_tema = ideia.resultado > 0
            state.preferencia_temas[tema] = state.preferencia_temas.get(tema, 0) + (1 if sucesso_para_preferencia_tema else -1)

            logger.info(
                "Prototipo/Execução de IDEIA '%s' concluído. Resultado financeiro: %.2f. Sucesso para tema: %s. Link produto: %s",
                ideia.descricao,
                ideia.resultado,
                sucesso_para_preferencia_tema,
                ideia.link_produto if ideia.link_produto else "N/A"
            )
            state.registrar_evento(
                f"Prototipo/Execução IDEIA '{ideia.descricao}'. Resultado: {ideia.resultado:.2f}. Sucesso p/ tema: {sucesso_para_preferencia_tema}. Link: {ideia.link_produto if ideia.link_produto else 'N/A'}"
            )


def executar_ciclo_criativo() -> None:
    """Executa um ciclo completo de ideação, validação e prototipagem para produtos e serviços."""

    # --- IDEAÇÃO (Produtos e Serviços) ---
    # A função propor_ideias() agora lida com ambos e adiciona diretamente aos históricos.
    # Portanto, não retorna mais uma lista para ser processada aqui.
    # Ela também registra os eventos e logs internamente.
    propor_ideias() # Esta função agora popula state.historico_ideias e state.historico_servicos

    # Lógica de fallback se nenhum produto ou serviço foi proposto por LLMs
    # Produtos:
    if not any(i for i in state.historico_ideias if i.executada is False): # Verifica se há novas ideias de produto não processadas
        if config.MODO_VIDA_INFINITA:
            state.registrar_evento("VIDA INFINITA: Gerando 3 ideias de PRODUTO automáticas (fallback).")
            logger.info("VIDA INFINITA: Nenhuma ideia de PRODUTO nova proposta por agentes. Gerando 3 ideias automáticas.")
            ideias_automaticas_produto = [
                Ideia(descricao="Produto Automático VIDA INFINITA: Super App vNext", autor="Sistema Infinito"),
                Ideia(descricao="Produto Automático VIDA INFINITA: Colonizador Espacial MkII", autor="Sistema Infinito"),
                Ideia(descricao="Produto Automático VIDA INFINITA: IA Consciente Beta", autor="Sistema Infinito")
            ]
            for ia_p in ideias_automaticas_produto:
                if ia_p not in state.historico_ideias: state.historico_ideias.append(ia_p)
        else:
            ideia_automatica_produto = Ideia(
                descricao="Ideia de produto genérica de otimização (fallback)",
                justificativa="Otimização de processos internos como produto (fallback).",
                autor="Sistema Criativo Automático (Produto Fallback)"
            )
            if ideia_automatica_produto not in state.historico_ideias:
                state.historico_ideias.append(ideia_automatica_produto)
                state.registrar_evento(f"Ideia de PRODUTO automática (fallback) gerada: {ideia_automatica_produto.descricao}")
                logger.info("Nenhuma ideia de PRODUTO nova proposta por agentes. Gerada ideia automática (fallback): %s", ideia_automatica_produto.descricao)

    # Serviços:
    # `propor_ideias` já lida com serviços. `propor_servicos` pode ser removida ou integrada.
    # Por agora, vamos verificar se `propor_ideias` adicionou algum serviço novo.
    # Consideramos "novo" um serviço que está no status 'proposed'.
    novos_servicos_propostos_no_ciclo = [s for s in state.historico_servicos if s.status == "proposed"]

    if not novos_servicos_propostos_no_ciclo:
        if config.MODO_VIDA_INFINITA:
            state.registrar_evento("VIDA INFINITA: Gerando 1 proposta de SERVIÇO automática (fallback).")
            logger.info("VIDA INFINITA: Nenhuma proposta de SERVIÇO nova. Gerando 1 proposta automática (fallback).")
            servico_automatico = Service(
                service_name="Consultoria Estratégica de IA (Automático VI Fallback)",
                description="Serviço de consultoria automática para empresas que buscam otimizar com IA (fallback).",
                author="Sistema Criativo Infinito (Serviço Fallback)",
                required_skills=["Consultor", "Analista IA"],
                estimated_effort_hours=20,
                pricing_model="fixed_price",
                price_amount=1000.0
            )
            if servico_automatico not in state.historico_servicos: # Evita duplicatas
                state.historico_servicos.append(servico_automatico)
        # else: # Não há fallback automático para serviços no modo normal ainda, a menos que queiramos adicionar.
        #     logger.info("Nenhum serviço novo proposto neste ciclo (nem fallback).")


    # --- VALIDAÇÃO (Unificada) ---
    # Coleta todas as ideias e serviços que precisam de validação
    ideias_necessitando_validacao = [i for i in state.historico_ideias if not i.validada and not i.executada]
    servicos_necessitando_validacao = [s for s in state.historico_servicos if s.status == "proposed"]

    if ideias_necessitando_validacao or servicos_necessitando_validacao:
        logger.info(f"Iniciando validação para {len(ideias_necessitando_validacao)} ideias e {len(servicos_necessitando_validacao)} serviços.")
        validar_propostas(ideias_necessitando_validacao, servicos_necessitando_validacao)
    else:
        logger.info("Nenhuma ideia ou serviço necessitando validação neste ciclo.")

    # --- PROTOTIPAGEM (Apenas Produtos por enquanto) ---
    # Prototipa ideias de produto validadas e ainda não executadas.
    ideias_para_prototipar = [i for i in state.historico_ideias if i.validada and not i.executada]
    if ideias_para_prototipar:
        prototipar_ideias(ideias_para_prototipar)
    else:
        logger.info("Nenhuma ideia de produto validada para prototipar neste ciclo.")


    # A remoção da função propor_servicos() e a integração completa de sua lógica
    # em propor_ideias() significa que não precisamos mais chamar propor_servicos() separadamente.
    # A função executar_ciclo_criativo agora usa diretamente os históricos que são
    # populados por propor_ideias().

    # NOTA: A "prototipagem" ou execução de serviços não está implementada aqui.
    # Isso exigiria uma lógica separada (ex: `executar_servicos_validados`).

    # Salvar históricos pode ser feito centralmente em empresa_digital.py após o ciclo.
    num_novas_ideias = len([i for i in state.historico_ideias if not i.executada]) # Aproximação de "novas" ou "ativas"
    num_novos_servicos = len([s for s in state.historico_servicos if s.status == 'proposed' or s.status == 'validated' or s.status == 'in_progress']) # Aproximação
    logger.info(f"Ciclo criativo concluído. Ideias de produto ativas: {num_novas_ideias}, Serviços propostos/ativos: {num_novos_servicos}")


def executar_servicos_validados() -> None:
    """
    Gerencia a execução de serviços validados, incluindo atribuição automática e simulação de progresso.
    """
    logger.info("Iniciando execução de serviços validados...")
    agentes_executores_disponiveis = [
        ag for ag_nome, ag in state.agentes.items()
        if ag.funcao.lower() == "executor" and (not ag.objetivo_atual or "aguardando" in ag.objetivo_atual.lower())
    ]

    # Determinar o fator de horas por ciclo
    current_hours_per_cycle = config.HOURS_PER_CYCLE_FACTOR_VIDA_INFINITA if config.MODO_VIDA_INFINITA else config.HOURS_PER_CYCLE_FACTOR

    for servico in state.historico_servicos:
        if servico.status == "validated":
            servico.cycles_unassigned += 1
            logger.info(f"Serviço '{servico.service_name}' (ID: {servico.id}) está validado há {servico.cycles_unassigned} ciclos.")
            if servico.cycles_unassigned >= 2:
                agente_atribuido = None
                if agentes_executores_disponiveis:
                    agente_atribuido = agentes_executores_disponiveis.pop(0) # Pega o primeiro executor livre
                    logger.info(f"Executor existente '{agente_atribuido.nome}' encontrado para o serviço '{servico.service_name}'.")
                else:
                    logger.info(f"Nenhum Executor livre. Contratando novo Executor para o serviço '{servico.service_name}'.")
                    # Usar rh.py para contratar seria ideal, mas por agora, criamos diretamente.
                    # Assumindo que rh.py tem uma função como modulo_rh.contratar_agente_especializado
                    # ou usamos criar_agente (from agent_utils) diretamente.
                    novo_executor_nome = f"Executor_{servico.service_name[:10].replace(' ', '_')}_{uuid.uuid4().hex[:4]}"

                    # Definir um local padrão para o novo agente, ex: o primeiro local da lista ou um específico
                    local_padrao_para_novos_agentes = list(state.locais.keys())[0] if state.locais else None
                    if not local_padrao_para_novos_agentes:
                        logger.error("Não há locais definidos. Impossível criar novo Executor.")
                        continue # Pula este serviço se não puder criar agente

                    modelo_llm_executor, _ = selecionar_modelo("Executor", f"Executar serviço {servico.service_name}") # Use from agent_utils

                    try:
                        agente_atribuido = criar_agente( # Use from agent_utils
                            nome=novo_executor_nome,
                            funcao="Executor",
                            modelo_llm=modelo_llm_executor,
                            local=local_padrao_para_novos_agentes, # Precisa ser um nome de local
                            objetivo=f"Executar serviço: {servico.service_name} (ID: {servico.id})"
                        )
                        logger.info(f"Novo Executor '{agente_atribuido.nome}' contratado e atribuído ao serviço '{servico.service_name}'.")
                        state.registrar_evento(f"Novo Executor '{agente_atribuido.nome}' contratado para '{servico.service_name}'.")
                    except ValueError as e:
                        logger.error(f"Falha ao criar novo Executor para o serviço '{servico.service_name}': {e}")
                        continue # Pula este serviço

                if agente_atribuido:
                    servico.assign_agent(agente_atribuido.nome, message="Auto-atribuído pelo sistema após 2 ciclos de espera.")
                    agente_atribuido.objetivo_atual = f"Executar serviço: {servico.service_name} (ID: {servico.id})"
                    logger.info(f"Serviço '{servico.service_name}' (ID: {servico.id}) auto-atribuído a '{agente_atribuido.nome}'.")
                    state.registrar_evento(f"Serviço '{servico.service_name}' auto-atribuído a '{agente_atribuido.nome}'. Objetivo atualizado.")
                    # servico.cycles_unassigned = 0 # assign_agent já faz isso
            else:
                logger.info(f"Serviço '{servico.service_name}' (ID: {servico.id}) aguardando atribuição por mais {2 - servico.cycles_unassigned} ciclos.")

        elif servico.status == "in_progress" and servico.assigned_agent_name:
            if servico.assigned_agent_name not in state.agentes:
                logger.warning(f"Agente '{servico.assigned_agent_name}' atribuído ao serviço '{servico.service_name}' (ID: {servico.id}) não encontrado. Serviço parado.")
                # Opcional: Mudar status para 'paused' ou 'problem'
                # servico.update_status("problem", "Agente atribuído não existe mais.")
                continue

            agente_executor = state.agentes[servico.assigned_agent_name]
            servico.progress_hours += current_hours_per_cycle
            logger.info(f"Serviço '{servico.service_name}' (ID: {servico.id}): Progresso {servico.progress_hours:.2f}/{servico.estimated_effort_hours} horas por {agente_executor.nome}.")
            servico.history.append({ # Adicionar log de progresso ao histórico do serviço
                "timestamp": str(time.time()),
                "status": "in_progress",
                "message": f"Progresso: {servico.progress_hours:.2f}/{servico.estimated_effort_hours}h. Agente: {agente_executor.nome}"
            })


            if servico.progress_hours >= servico.estimated_effort_hours:
                servico.complete_service(message="Concluído via simulação de progresso.")
                logger.info(f"Serviço '{servico.service_name}' (ID: {servico.id}) CONCLUÍDO por {agente_executor.nome}.")
                state.registrar_evento(f"Serviço '{servico.service_name}' (ID: {servico.id}) CONCLUÍDO por {agente_executor.nome}.")

                # Limpar objetivo do agente
                if agente_executor.objetivo_atual == f"Executar serviço: {servico.service_name} (ID: {servico.id})":
                    agente_executor.objetivo_atual = "Aguardando novas atribuições."
                    logger.info(f"Objetivo de {agente_executor.nome} resetado para 'Aguardando novas atribuições'.")
                    state.registrar_evento(f"Objetivo de {agente_executor.nome} resetado.")
                # A receita será calculada em ed.calcular_lucro_ciclo()
    logger.info("Execução de serviços validados concluída.")
