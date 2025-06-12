import logging
from typing import Tuple, Optional, List, Dict
import json # For chamar_openrouter_api
import time # For chamar_openrouter_api
import requests # For chamar_openrouter_api

from core_types import Agente, Local
import state
import config # For OPENROUTER_CALL_DELAY_SECONDS
from openrouter_utils import obter_api_key, buscar_modelos_gratis, escolher_modelo_llm

# Logger for this module
logger = logging.getLogger(__name__)

def selecionar_modelo(funcao: str, objetivo: str = "") -> Tuple[str, str]:
    """Escolhe dinamicamente o modelo de linguagem para um agente."""
    heuristicas = {"Dev": "deepseek-chat", "CEO": "phi-4:free"}
    if funcao in heuristicas:
        modelo = heuristicas[funcao]
        raciocinio = "heuristica"
    else:
        modelos = buscar_modelos_gratis()
        modelo, raciocinio = escolher_modelo_llm(funcao, objetivo, modelos)
    logger.info(
        "Modelo %s escolhido para funcao %s - %s", modelo, funcao, raciocinio
    )
    return modelo, raciocinio

def criar_agente(
    nome: str,
    funcao: str,
    modelo_llm: str,
    local: str,
    objetivo: str = ""
) -> Agente:
    local_obj = state.locais.get(local)
    if local_obj is None:
        logger.error(f"Tentativa de criar agente '{nome}' no local '{local}' que não existe.")
        raise ValueError(f"Local '{local}' não encontrado.")
    agente = Agente(
        nome=nome,
        funcao=funcao,
        modelo_llm=modelo_llm,
        local_atual=local_obj,
        objetivo_atual=objetivo,
    )
    state.agentes[nome] = agente
    local_obj.adicionar_agente(agente)
    agente.historico_locais.append(local_obj.nome)
    logger.info(f"Agente '{nome}' criado na função '{funcao}' no local '{local}'.")
    return agente

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
        ("Colegas presentes: " + (", ".join(colegas) if colegas else "Nenhum")),
        ("Inventário disponível: " + (", ".join(local.inventario) if local.inventario else "Nenhum")),
        ("Últimas ações: " + (" | ".join(agente.historico_acoes[-3:]) if agente.historico_acoes else "Nenhuma")),
        ("Últimas interações: " + (" | ".join(agente.historico_interacoes[-3:]) if agente.historico_interacoes else "Nenhuma")),
        ("Últimos locais: " + (" -> ".join(agente.historico_locais[-2:]) if agente.historico_locais else "Nenhum")),
        f"Objetivo atual: {agente.objetivo_atual or 'Nenhum'}",
        "Objetivo principal: maximizar o lucro da empresa de forma autônoma e criativa",
        f"Feedback do CEO: {agente.feedback_ceo or 'Nenhum'}",
        f"Estado emocional: {agente.estado_emocional}",
    ]
    return "\n".join(partes)

def chamar_openrouter_api(agente: Agente, prompt: str) -> str:
    time.sleep(config.OPENROUTER_CALL_DELAY_SECONDS)
    logger.debug(f"Iniciando chamada para OpenRouter API para o agente {agente.nome} com modelo {agente.modelo_llm}.")
    logger.debug(f"Prompt enviado para OpenRouter (modelo {agente.modelo_llm}):\n{prompt}")
    MAX_RETRIES = 3
    INITIAL_BACKOFF_DELAY = 1
    RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
    api_key = obter_api_key()
    if not api_key:
        logger.error("OPENROUTER_API_KEY não configurada.")
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
            logger.debug(f"Tentativa {attempt + 1}: Resposta crua da OpenRouter (status {response.status_code}): {response.text}")
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
                    logger.error("Estrutura de resposta da API OpenRouter inesperada: %s", response_data)
                    return json.dumps({"error": "Invalid response structure", "details": "Unexpected API response format."})
            elif response.status_code in RETRYABLE_STATUS_CODES:
                if attempt < MAX_RETRIES - 1:
                    backoff_time = INITIAL_BACKOFF_DELAY * (2 ** attempt)
                    logger.warning(
                        f"Erro {response.status_code} na tentativa {attempt + 1} para o agente {agente.nome}. "
                        f"Tentando novamente em {backoff_time} segundos..."
                    )
                    time.sleep(backoff_time)
                    continue
                else:
                    logger.error(
                        f"Erro {response.status_code} na API OpenRouter para o agente {agente.nome} após {MAX_RETRIES} tentativas. "
                        f"Detalhes: {response.text}"
                    )
                    return json.dumps({"error": f"Erro na API OpenRouter: {response.status_code}", "details": response.text})
            else:
                logger.error(
                    f"Erro não recuperável {response.status_code} na API OpenRouter para o agente {agente.nome}. "
                    f"Detalhes: {response.text}"
                )
                response.raise_for_status()
                return json.dumps({"error": f"Erro na API OpenRouter: {response.status_code}", "details": response.text})
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout na tentativa {attempt + 1} para a API OpenRouter (agente {agente.nome}): {e}")
            if attempt < MAX_RETRIES - 1:
                backoff_time = INITIAL_BACKOFF_DELAY * (2 ** attempt)
                logger.info(f"Tentando novamente em {backoff_time} segundos...")
                time.sleep(backoff_time)
                continue
            else:
                logger.error(f"Timeout final após {MAX_RETRIES} tentativas para o agente {agente.nome}: {e}")
                return json.dumps({"error": "API call failed", "details": "Request timed out after multiple retries."})
        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de requisição na tentativa {attempt + 1} para a API OpenRouter (agente {agente.nome}): {e}")
            if attempt < MAX_RETRIES - 1:
                backoff_time = INITIAL_BACKOFF_DELAY * (2 ** attempt)
                logger.info(f"Tentando novamente em {backoff_time} segundos...")
                time.sleep(backoff_time)
                continue
            else:
                logger.error(f"Erro final de requisição após {MAX_RETRIES} tentativas para o agente {agente.nome}: {e}")
                return json.dumps({"error": "API call failed", "details": str(e)})
        except json.JSONDecodeError as e:
            logger.error(f"Erro ao decodificar JSON da resposta da API OpenRouter para o agente {agente.nome}: {e}. Resposta: {response.text if 'response' in locals() and hasattr(response, 'text') else 'N/A'}")
            return json.dumps({"error": "API call failed", "details": "Invalid JSON response from API."})
        except (KeyError, IndexError, TypeError) as e:
            logger.error(f"Erro ao processar estrutura da resposta da API OpenRouter para o agente {agente.nome}: {e}")
            return json.dumps({"error": "Invalid response structure", "details": str(e)})
    logger.error(f"A função chamar_openrouter_api terminou inesperadamente para o agente {agente.nome}.")
    return json.dumps({"error": "API call failed", "details": "Unknown error after retries."})

def enviar_para_llm(agente: Agente, prompt: str) -> str:
    state.registrar_evento(f"Prompt para {agente.nome}")
    logger.info(f"Enviando prompt para LLM {agente.modelo_llm} para o agente {agente.nome}.")
    resposta_llm = chamar_openrouter_api(agente, prompt)
    state.registrar_evento(f"Resposta recebida de {agente.modelo_llm} para {agente.nome}: {resposta_llm[:200]}...")
    logger.debug(f"Resposta completa de {agente.modelo_llm} para {agente.nome}: {resposta_llm}")
    return resposta_llm
