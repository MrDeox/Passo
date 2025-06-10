import logging
from dataclasses import asdict # dataclass is now in core_types
from typing import List, Dict, Optional
import json # Added for saving/loading historico_ideias
import time # For timestamps in Service history
import uuid # For Service IDs

import empresa_digital as ed
from .core_types import Ideia, Service # Import Ideia and Service from core_types
from .criador_de_produtos import produto_digital
from .divulgador import sugerir_conteudo_marketing # Import for Divulgador

logger = logging.getLogger(__name__)

# Ideia dataclass definition is removed from here

historico_ideias: List[Ideia] = [] # Now uses Ideia from core_types
historico_servicos: List[Service] = [] # New history for services
preferencia_temas: Dict[str, int] = {}


def salvar_historico_ideias(filename="historico_ideias.json"):
    """Salva o historico_ideias em um arquivo JSON."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # Convert Ideia objects to dictionaries for JSON serialization
            json.dump([asdict(ideia) for ideia in historico_ideias], f, ensure_ascii=False, indent=4)
        logger.info(f"Histórico de ideias salvo em {filename}")
    except IOError as e:
        logger.error(f"Erro ao salvar histórico de ideias: {e}")

def carregar_historico_ideias(filename="historico_ideias.json") -> List[Ideia]:
    """Carrega o historico_ideias de um arquivo JSON."""
    global historico_ideias # Allow modification of the global variable
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            ideias_data = json.load(f)
            # Convert dictionaries back to Ideia objects
            historico_ideias = [Ideia(**data) for data in ideias_data]
            logger.info(f"Histórico de ideias carregado de {filename}")
            return historico_ideias
    except FileNotFoundError:
        logger.warning(f"Arquivo de histórico de ideias '{filename}' não encontrado. Iniciando com histórico vazio.")
        historico_ideias = []
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do histórico de ideias: {e}. Iniciando com histórico vazio.")
        historico_ideias = []
        return []
    except Exception as e: # Catch other potential errors during loading (e.g., TypeError if Ideia structure changed)
        logger.error(f"Erro inesperado ao carregar histórico de ideias: {e}. Iniciando com histórico vazio.")
        historico_ideias = []
        return []


def salvar_historico_servicos(filename="servicos.json"):
    """Salva o historico_servicos em um arquivo JSON."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump([asdict(servico) for servico in historico_servicos], f, ensure_ascii=False, indent=4)
        logger.info(f"Histórico de serviços salvo em {filename}")
    except IOError as e:
        logger.error(f"Erro ao salvar histórico de serviços: {e}")

def carregar_historico_servicos(filename="servicos.json") -> List[Service]:
    """Carrega o historico_servicos de um arquivo JSON."""
    global historico_servicos
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
            historico_servicos = loaded_services
            logger.info(f"Histórico de serviços carregado de {filename}. {len(historico_servicos)} serviços carregados.")
            return historico_servicos
    except FileNotFoundError:
        logger.warning(f"Arquivo de histórico de serviços '{filename}' não encontrado. Iniciando com histórico vazio.")
        historico_servicos = []
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do histórico de serviços: {e}. Iniciando com histórico vazio.")
        historico_servicos = []
        return []
    except Exception as e:
        logger.error(f"Erro inesperado ao carregar histórico de serviços: {e}. Iniciando com histórico vazio.")
        historico_servicos = []
        return []


def _tema_preferido() -> str:
    """Define o tema a ser priorizado conforme resultados anteriores."""
    if not preferencia_temas:
        return "IA"
    return max(preferencia_temas, key=preferencia_temas.get)


def propor_ideias() -> List[Ideia]:
    """
    Gera ideias de PRODUTOS simuladas a partir de agentes com funcao 'Ideacao'.
    O LLM decide se quer propor um produto ou um serviço.
    Esta função lida apenas com a parte de PRODUTO.
    """
    ideias_produto_propostas = []
    tema = _tema_preferido() # Mantém a lógica de tema para produtos por enquanto

    agentes_ideacao = [ag for ag in ed.agentes.values() if ag.funcao.lower() == "ideacao"]
    if not agentes_ideacao:
        logger.info("Nenhum agente de 'Ideacao' encontrado para propor ideias de produtos.")
        return []

    for ag in agentes_ideacao:
        # Para simplificar, vamos manter a proposta de ideia de produto como antes,
        # e a proposta de serviço será separada ou o LLM decidirá o tipo.
        # Por enquanto, esta função foca em produtos.
        # A decisão de propor produto OU serviço será feita no prompt do agente.
        # Aqui, apenas criamos uma ideia de produto simples se o agente decidir por isso.
        # A lógica mais complexa de decisão do LLM virá depois.

        # Exemplo simplificado: O agente sempre propõe uma ideia de produto aqui.
        # A sofisticação para o LLM escolher entre produto/serviço e retornar
        # uma estrutura JSON diferenciada será adicionada na próxima etapa.
        desc = f"Produto {tema} proposto por {ag.nome} (foco: produto)"
        justificativa = f"Explora {tema} com alto potencial de lucro (foco: produto)"
        ideia = Ideia(descricao=desc, justificativa=justificativa, autor=ag.nome)
        ideias_produto_propostas.append(ideia)
        logger.info("Ideia de PRODUTO proposta: %s", desc)
        ed.registrar_evento(f"Ideia de PRODUTO proposta: {desc} por {ag.nome}")

    return ideias_produto_propostas


def propor_servicos() -> List[Service]:
    """
    Gera propostas de SERVIÇOS a partir de agentes com funcao 'Ideacao'.
    O LLM do agente deve ser instruído a fornecer os detalhes do serviço.
    """
    servicos_propostos = []
    agentes_ideacao = [ag for ag in ed.agentes.values() if ag.funcao.lower() == "ideacao"]

    if not agentes_ideacao:
        logger.info("Nenhum agente de 'Ideacao' encontrado para propor serviços.")
        return []

    for agente in agentes_ideacao:
        # Prompt para o LLM do agente de ideação
        # Este prompt precisa ser mais elaborado para pedir detalhes do serviço
        # e especificar o formato JSON esperado para um serviço.
        contexto_agente = ed.gerar_prompt_dinamico(agente)
        prompt_servico = f"""{contexto_agente}
Você é um agente de ideação. Sua tarefa é propor um novo SERVIÇO para a empresa.
Pense em um serviço que poderia ser lucrativo e viável com as (hipotéticas) capacidades da empresa.
Detalhe o serviço proposto no seguinte formato JSON. Responda APENAS com o JSON:
{{
  "type": "service",
  "service_name": "Nome do Serviço",
  "description": "Descrição detalhada do serviço e o que ele entrega.",
  "required_skills": ["Habilidade1", "Habilidade2", "FuncaoAgenteRelevante"],
  "estimated_effort_hours": 50,
  "pricing_model": "fixed_price", // ou "hourly_rate"
  "price_amount": 2500.00 // Preço total ou taxa horária
}}
Se você não conseguir propor um serviço ou achar que não é o momento, responda com: {{"type": "none"}}
"""
        logger.debug(f"Prompt de proposta de serviço para {agente.nome}:\n{prompt_servico}")
        resposta_llm_raw = ed.enviar_para_llm(agente, prompt_servico)

        try:
            resposta_json = json.loads(resposta_llm_raw)
            if isinstance(resposta_json, dict) and resposta_json.get("type") == "service":
                novo_servico = Service(
                    service_name=resposta_json.get("service_name", "Serviço Sem Nome"),
                    description=resposta_json.get("description", "Sem descrição detalhada."),
                    author=agente.nome,
                    required_skills=resposta_json.get("required_skills", []),
                    estimated_effort_hours=resposta_json.get("estimated_effort_hours", 0),
                    pricing_model=resposta_json.get("pricing_model", "fixed_price"),
                    price_amount=resposta_json.get("price_amount", 0.0),
                    # id, creation_timestamp, status, history são definidos no __init__ ou __post_init__
                )
                servicos_propostos.append(novo_servico)
                logger.info(f"Serviço proposto por {agente.nome}: '{novo_servico.service_name}' (ID: {novo_servico.id})")
                ed.registrar_evento(f"Novo SERVIÇO proposto: '{novo_servico.service_name}' por {agente.nome}")
            elif isinstance(resposta_json, dict) and resposta_json.get("type") == "none":
                logger.info(f"Agente {agente.nome} decidiu não propor um serviço desta vez.")
            else:
                logger.warning(f"Resposta LLM para proposta de serviço de {agente.nome} não reconhecida ou tipo incorreto: {resposta_llm_raw}")
                # Registrar uma falha na ação do agente pode ser feito aqui se necessário
        except json.JSONDecodeError:
            logger.error(f"Falha ao decodificar JSON da resposta LLM para proposta de serviço de {agente.nome}: {resposta_llm_raw}")
        except Exception as e:
            logger.error(f"Erro ao processar proposta de serviço de {agente.nome}: {e}. Resposta LLM: {resposta_llm_raw}", exc_info=True)

    return servicos_propostos


def validar_ideias(ideias_para_validar: List[Ideia]) -> None:
    """Valida as ideias de PRODUTO usando agentes com funcao 'Validador'."""
    validadores = [a for a in ed.agentes.values() if a.funcao.lower() == "validador"]
    if not validadores:
        logger.warning("Nenhum agente 'Validador' encontrado para validar ideias de produtos.")
        # Marcar todas as ideias como não validadas ou alguma outra lógica de fallback
        for ideia in ideias_para_validar:
            ideia.validada = False # Ou manter como está, dependendo da política
        return

    for ideia in ideias_para_validar:
        if ideia.validada: # Já validada anteriormente
            continue

        # Exemplo simplificado: Validação por LLM (a ser implementado de forma mais robusta)
        # Por enquanto, mantém a lógica original de validação de produto.
        validador_escolhido = validadores[0] # Simplista: pega o primeiro validador

        # Aqui, o prompt para o LLM do validador de PRODUTO seria construído.
        # Por ora, a lógica antiga é mantida para focar na estrutura do serviço.
        aprovado = "ia" in ideia.descricao.lower() # Lógica de validação original e simplista

        logger.info(
            "Validacao de IDEIA DE PRODUTO '%s' por %s: %s",
            ideia.descricao,
            validador_escolhido.nome,
            "aprovada" if aprovado else "reprovada",
        )
        ed.registrar_evento(
            f"Validacao de IDEIA DE PRODUTO '{ideia.descricao}' por {validador_escolhido.nome}: {'aprovada' if aprovado else 'reprovada'}"
        )
        if aprovado:
            ideia.validada = True
            # ed.adicionar_tarefa(f"Prototipar produto: {ideia.descricao}") # Tarefa para produto
        # Se reprovada, a ideia simplesmente não terá `ideia.validada = True`

def validar_servicos(servicos_para_validar: List[Service]) -> None:
    """Valida as propostas de SERVIÇO usando agentes com funcao 'Validador'."""
    validadores = [a for a in ed.agentes.values() if a.funcao.lower() == "validador"]
    if not validadores:
        logger.warning("Nenhum agente 'Validador' encontrado para validar propostas de serviços.")
        for servico in servicos_para_validar:
            if servico.status == "proposed": # Só tenta validar se ainda está proposto
                 servico.update_status("rejected", "Validação automática: Nenhum validador disponível.")
        return

    for servico in servicos_para_validar:
        if servico.status != "proposed": # Só valida se está no estado "proposed"
            logger.info(f"Serviço '{servico.service_name}' (ID: {servico.id}) já foi processado (status: {servico.status}). Pulando validação.")
            continue

        validador_escolhido = validadores[0] # Simplista: pega o primeiro

        # TODO: Melhorar a lógica de quais habilidades estão disponíveis na empresa.
        # Por enquanto, o LLM pode ter que inferir ou podemos passar uma lista simplificada.
        habilidades_disponiveis_simples = list(set(ag.funcao for ag in ed.agentes.values()))


        contexto_validador = ed.gerar_prompt_dinamico(validador_escolhido)
        prompt_validacao_servico = f"""{contexto_validador}
Você é um agente Validador. Sua tarefa é analisar a seguinte proposta de SERVIÇO e decidir se deve ser 'aprovada' ou 'rejeitada'.
Leve em consideração a descrição, habilidades requeridas, esforço estimado e preço.
Habilidades/Funções de agentes disponíveis na empresa (simplificado): {', '.join(habilidades_disponiveis_simples)}.

Detalhes da Proposta de Serviço:
ID: {servico.id}
Nome: {servico.service_name}
Descrição: {servico.description}
Autor: {servico.author}
Habilidades Requeridas: {', '.join(servico.required_skills)}
Esforço Estimado (horas): {servico.estimated_effort_hours}
Modelo de Preço: {servico.pricing_model}
Valor/Taxa: {servico.price_amount}

Responda APENAS com um JSON contendo sua decisão e uma breve justificativa:
{{
  "service_id": "{servico.id}",
  "decision": "aprovada", // ou "rejeitada"
  "justification": "A proposta parece viável e alinhada com os objetivos da empresa."
}}
"""
        logger.debug(f"Prompt de validação de serviço para {validador_escolhido.nome}:\n{prompt_validacao_servico}")
        resposta_llm_raw = ed.enviar_para_llm(validador_escolhido, prompt_validacao_servico)

        try:
            resposta_json = json.loads(resposta_llm_raw)
            if isinstance(resposta_json, dict) and resposta_json.get("service_id") == servico.id:
                decisao = resposta_json.get("decision")
                justificativa = resposta_json.get("justification", "Sem justificativa fornecida.")

                if decisao == "aprovada":
                    servico.update_status("validated", f"Validado por {validador_escolhido.nome}: {justificativa}")
                    logger.info(f"SERVIÇO '{servico.service_name}' (ID: {servico.id}) APROVADO por {validador_escolhido.nome}. Justificativa: {justificativa}")
                    ed.registrar_evento(f"SERVIÇO '{servico.service_name}' APROVADO. Validador: {validador_escolhido.nome}. Justificativa: {justificativa}")
                    # ed.adicionar_tarefa(f"Iniciar execução do serviço: {servico.service_name} (ID: {servico.id})")
                elif decisao == "rejeitada":
                    servico.update_status("rejected", f"Rejeitado por {validador_escolhido.nome}: {justificativa}")
                    logger.info(f"SERVIÇO '{servico.service_name}' (ID: {servico.id}) REJEITADO por {validador_escolhido.nome}. Justificativa: {justificativa}")
                    ed.registrar_evento(f"SERVIÇO '{servico.service_name}' REJEITADO. Validador: {validador_escolhido.nome}. Justificativa: {justificativa}")
                else:
                    logger.warning(f"Decisão de validação de serviço '{decisao}' não reconhecida para o serviço ID {servico.id} por {validador_escolhido.nome}. Resposta: {resposta_llm_raw}")
                    servico.update_status("rejected", f"Falha na validação (decisão inválida) por {validador_escolhido.nome}: {justificativa}")
            else:
                logger.warning(f"Resposta LLM para validação de serviço de {validador_escolhido.nome} com ID de serviço incorreto ou formato inválido: {resposta_llm_raw}")
                servico.update_status("rejected", f"Falha na validação (resposta LLM inválida) por {validador_escolhido.nome}.")
        except json.JSONDecodeError:
            logger.error(f"Falha ao decodificar JSON da resposta LLM para validação de serviço de {validador_escolhido.nome}: {resposta_llm_raw}")
            servico.update_status("rejected", f"Falha na validação (JSON inválido) por {validador_escolhido.nome}.")
        except Exception as e:
            logger.error(f"Erro ao processar validação de serviço ID {servico.id} por {validador_escolhido.nome}: {e}. Resposta LLM: {resposta_llm_raw}", exc_info=True)
            servico.update_status("rejected", f"Falha na validação (erro interno) por {validador_escolhido.nome}.")


def prototipar_ideias(ideias: List[Ideia]) -> None:
    """Simula prototipagem gerando lucro ou prejuizo."""
    for ideia in ideias:
        if not ideia.validada:
            continue

        # Tentativa de criar produto digital se ainda não foi criado
        if ideia.link_produto is None:
            logger.info(f"Tentando criar produto digital para ideia validada: {ideia.descricao}")
            try:
                # ed.agentes e ed.locais são acessados globalmente a partir de empresa_digital importado como ed
                product_url = produto_digital(ideia, ed.agentes, ed.locais)
                if product_url:
                    ideia.link_produto = product_url
                    # Evento de criação de produto já é registrado em produto_digital.py
                    logger.info(f"Produto '{ideia.descricao}' criado com sucesso: {product_url}")

                    # >>> Integration of Divulgador <<<
                    logger.info(f"Tentando gerar sugestões de marketing para '{ideia.descricao}'...")
                    marketing_sugestoes = sugerir_conteudo_marketing(ideia, product_url)
                    if marketing_sugestoes:
                        # Logging e registro de evento são feitos dentro de sugerir_conteudo_marketing
                        logger.info(f"Sugestões de marketing geradas para '{ideia.descricao}'.")
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
                    ed.registrar_evento(f"Falha na criação do produto para ideia: {ideia.descricao}")
                    ideia.resultado = -15.0 # Penalidade maior se a criação do produto falhar
            except Exception as e:
                logger.error(f"Exceção ao tentar criar produto digital para '{ideia.descricao}': {e}", exc_info=True)
                ed.registrar_evento(f"Exceção na criação do produto para ideia '{ideia.descricao}': {e}")
                ideia.resultado = -20.0 # Penalidade por exceção

        # Lógica de simulação de prototipagem/resultado (executada mesmo se o produto já existia ou falhou, mas com resultado já ajustado)
        if not ideia.executada:
            ideia.executada = True
            # Se o resultado não foi definido pela lógica de criação de produto (ex: ideia já tinha link_produto)
            # ou se queremos adicionar mais alguma lógica de resultado baseada em 'sucesso'
            if ideia.resultado == 0.0 and not ideia.link_produto : # Só aplica resultado padrão se não foi tocado pela criação de produto.
                sucesso_prototipagem = "ia" in ideia.descricao.lower() # Condição de sucesso original
                ideia.resultado = 30.0 if sucesso_prototipagem else -10.0

            tema = "IA" if "ia" in ideia.descricao.lower() else "outros" # TODO: Melhorar extração de tema
            preferencia_temas[tema] = preferencia_temas.get(tema, 0) + (1 if sucesso else -1)
            logger.info(
                "Prototipo/Execução de %s resultou em %.2f (Link produto: %s)",
                ideia.descricao,
                ideia.resultado,
                ideia.link_produto if ideia.link_produto else "N/A"
            )
            ed.registrar_evento(
                f"Prototipo/Execução de {ideia.descricao} resultou em {ideia.resultado:.2f}. Link: {ideia.link_produto if ideia.link_produto else 'N/A'}"
            )


def executar_ciclo_criativo() -> None:
    """Executa um ciclo completo de ideação, validação e prototipagem para produtos e serviços."""

    # --- PRODUTOS ---
    ideias_de_produto = propor_ideias() # Focado em produtos
    if not ideias_de_produto:
        if ed.MODO_VIDA_INFINITA: # Lógica de fallback para produtos
            ed.registrar_evento("VIDA INFINITA: Gerando 3 ideias de PRODUTO automáticas.")
            logger.info("VIDA INFINITA: Nenhuma ideia de PRODUTO proposta por agentes. Gerando 3 ideias automáticas.")
            # ... (código de geração de ideias automáticas de produto mantido como antes)
            ideias_automaticas_produto = [
                Ideia(descricao="Produto Automático VIDA INFINITA: Super App", autor="Sistema Infinito"),
                Ideia(descricao="Produto Automático VIDA INFINITA: Colonizador Espacial", autor="Sistema Infinito"),
                Ideia(descricao="Produto Automático VIDA INFINITA: IA Consciente", autor="Sistema Infinito")
            ]
            ideias_de_produto.extend(ideias_automaticas_produto)
        else:
            ideia_automatica_produto = Ideia(
                descricao="Ideia de produto genérica de otimização",
                justificativa="Otimização de processos internos como produto.",
                autor="Sistema Criativo Automático (Produto)"
            )
            ideias_de_produto.append(ideia_automatica_produto)
            ed.registrar_evento(f"Ideia de PRODUTO automática gerada: {ideia_automatica_produto.descricao}")
            logger.info("Nenhuma ideia de PRODUTO proposta por agentes. Gerada ideia automática: %s", ideia_automatica_produto.descricao)

    validar_ideias(ideias_de_produto) # Valida apenas produtos
    prototipar_ideias(ideias_de_produto) # Prototipa apenas produtos

    # Adiciona todas as ideias de produto (novas e as que já estavam no histórico e foram re-processadas)
    # É importante garantir que não haja duplicatas se `propor_ideias` puder retornar ideias já existentes.
    # A lógica atual de `propor_ideias` sempre cria novas.
    for ideia_p in ideias_de_produto:
        if ideia_p not in historico_ideias: # Evita duplicatas se a lógica de proposta mudar
            historico_ideias.append(ideia_p)

    # --- SERVIÇOS ---
    servicos_propostos = propor_servicos()
    if not servicos_propostos and not ed.MODO_VIDA_INFINITA: # Não há fallback automático para serviços no modo normal ainda
        logger.info("Nenhum serviço proposto neste ciclo.")
    elif not servicos_propostos and ed.MODO_VIDA_INFINITA:
        ed.registrar_evento("VIDA INFINITA: Gerando 1 proposta de SERVIÇO automática.")
        logger.info("VIDA INFINITA: Nenhuma proposta de SERVIÇO. Gerando 1 proposta automática.")
        servico_automatico = Service(
            service_name="Consultoria Estratégica de IA (Automático VI)",
            description="Serviço de consultoria automática para empresas que buscam otimizar com IA.",
            author="Sistema Criativo Infinito (Serviço)",
            required_skills=["Consultor", "Analista IA"],
            estimated_effort_hours=20,
            pricing_model="fixed_price",
            price_amount=1000.0
        )
        servicos_propostos.append(servico_automatico)

    validar_servicos(servicos_propostos)

    # Adiciona todos os serviços propostos (novos) ao histórico de serviços.
    # Similar às ideias, garantir que não haja duplicatas se a lógica mudar.
    for servico_p in servicos_propostos:
        if servico_p not in historico_servicos: # Evita duplicatas
            historico_servicos.append(servico_p)

    # NOTA: A "prototipagem" ou execução de serviços não está implementada aqui.
    # Isso exigiria uma lógica separada (ex: `executar_servicos_validados`).
    # Por enquanto, o ciclo criativo para serviços vai até a validação.

    # Salvar históricos pode ser feito centralmente em empresa_digital.py após o ciclo.
    logger.info(f"Ciclo criativo concluído. Ideias de produto: {len(ideias_de_produto)}, Serviços propostos: {len(servicos_propostos)}")
