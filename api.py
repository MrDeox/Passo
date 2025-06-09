import logging
from typing import List, Optional, Tuple
import requests

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from empresa_digital import (
    Agente,
    Local,
    agentes,
    locais,
    saldo,
    historico_saldo,
    calcular_lucro_ciclo,
    criar_agente,
    criar_local,
    mover_agente,
    gerar_prompt_decisao,
    enviar_para_llm,
    executar_resposta,
)
from rh import modulo_rh
from ciclo_criativo import executar_ciclo_criativo, historico_ideias

# Configuração de logging global
logging.basicConfig(level=logging.INFO)

# Instância principal da aplicação FastAPI
app = FastAPI(title="Empresa Digital API")


def agente_to_dict(ag: Agente) -> dict:
    """Converte um agente para um dicionário serializável."""
    return {
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


def local_to_dict(loc: Local) -> dict:
    """Converte um local para um dicionário serializável."""
    return {
        "nome": loc.nome,
        "descricao": loc.descricao,
        "inventario": loc.inventario,
        "agentes_presentes": [a.nome for a in loc.agentes_presentes],
    }


class AgentIn(BaseModel):
    """Modelo de dados para criar agentes."""

    nome: str
    funcao: str
    modelo_llm: str
    local: str
    objetivo: Optional[str] = ""


class AgentUpdate(BaseModel):
    """Modelo para atualizar atributos de um agente."""

    funcao: Optional[str] = None
    modelo_llm: Optional[str] = None
    local: Optional[str] = None
    objetivo: Optional[str] = None
    feedback_ceo: Optional[str] = None


class LocalIn(BaseModel):
    """Modelo de dados para criar locais."""

    nome: str
    descricao: str
    inventario: Optional[List[str]] = None


class LocalUpdate(BaseModel):
    """Modelo de dados para atualizar locais."""

    descricao: Optional[str] = None
    inventario: Optional[List[str]] = None


class EscolherModeloIn(BaseModel):
    """Dados enviados para decidir o melhor modelo para o agente."""

    nome: str
    funcao: str
    sala: str


class ModeloEscolhido(BaseModel):
    """Resposta contendo o modelo definido automaticamente."""

    modelo: str
    raciocinio: str


def _buscar_modelos_gratis() -> List[str]:
    """Retorna todos os modelos gratuitos dispon\u00edveis na OpenRouter."""
    url = "https://openrouter.ai/api/v1/models"
    resp = requests.get(url, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [m["id"] for m in data.get("data", []) if ":free" in m.get("id", "")]


def _escolher_modelo(funcao: str, modelos: List[str]) -> Tuple[str, str]:
    """Decide qual modelo usar de forma simplificada."""
    f = funcao.lower()
    # Heuristica simples para demonstracao, substitui uma chamada real a um LLM
    if any(term in f for term in ["dev", "engenheiro", "developer"]):
        for m in modelos:
            if "deepseek" in m:
                return (
                    m,
                    "Funcao tecnica detectada; modelo DeepSeek escolhido por ser otimizado para codigo.",
                )
    if any(term in f for term in ["ceo", "diretor", "gerente"]):
        for m in modelos:
            if "phi-4" in m or "llama" in m:
                return (
                    m,
                    "Funcao gerencial; modelo avançado selecionado para apoio estrategico.",
                )
    return (
        modelos[0] if modelos else "",
        "Funcao generica; primeiro modelo gratuito utilizado.",
    )


# ---------------------------- Endpoints de agentes ----------------------------

@app.get("/modelos-livres", response_model=List[str])
def modelos_livres_endpoint():
    """Lista todos os modelos gratuitos retornados pela OpenRouter."""
    try:
        return _buscar_modelos_gratis()
    except Exception as exc:
        logging.error("Erro ao buscar modelos: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/agentes/escolher-modelo", response_model=ModeloEscolhido)
def escolher_modelo_endpoint(dados: EscolherModeloIn):
    """Determina automaticamente o modelo de LLM para um novo agente."""
    modelos = _buscar_modelos_gratis()
    modelo, motivo = _escolher_modelo(dados.funcao, modelos)
    logging.info("Modelo %s escolhido para %s - %s", modelo, dados.nome, motivo)
    return ModeloEscolhido(modelo=modelo, raciocinio=motivo)

@app.get("/agentes")
async def listar_agentes():
    """Retorna todos os agentes e suas informações."""
    return [agente_to_dict(a) for a in agentes.values()]


@app.get("/agentes/{nome}")
async def obter_agente(nome: str):
    """Recupera um único agente pelo nome."""
    ag = agentes.get(nome)
    if ag is None:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")
    return agente_to_dict(ag)


@app.post("/agentes", status_code=201)
async def criar_agente_endpoint(dados: AgentIn):
    """Cria um novo agente."""
    if dados.nome in agentes:
        raise HTTPException(status_code=400, detail="Agente ja existe")
    criar_agente(
        dados.nome,
        dados.funcao,
        dados.modelo_llm,
        dados.local,
        dados.objetivo,
    )
    return agente_to_dict(agentes[dados.nome])


@app.put("/agentes/{nome}")
async def editar_agente(nome: str, dados: AgentUpdate):
    """Edita atributos de um agente existente."""
    ag = agentes.get(nome)
    if ag is None:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")
    if dados.funcao is not None:
        ag.funcao = dados.funcao
    if dados.modelo_llm is not None:
        ag.modelo_llm = dados.modelo_llm
    if dados.objetivo is not None:
        ag.objetivo_atual = dados.objetivo
    if dados.feedback_ceo is not None:
        ag.feedback_ceo = dados.feedback_ceo
    if dados.local is not None:
        mover_agente(nome, dados.local)
    return agente_to_dict(ag)


@app.delete("/agentes/{nome}")
async def remover_agente(nome: str):
    """Remove um agente do sistema."""
    ag = agentes.pop(nome, None)
    if ag is None:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")
    if ag.local_atual:
        ag.local_atual.remover_agente(ag)
    return {"ok": True}


# ------------------------------ Endpoints locais -----------------------------
@app.get("/locais")
async def listar_locais():
    """Lista todos os locais e quem está em cada um."""
    return [local_to_dict(l) for l in locais.values()]


@app.get("/locais/{nome}")
async def obter_local(nome: str):
    """Recupera um local específico."""
    loc = locais.get(nome)
    if loc is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado")
    return local_to_dict(loc)


@app.post("/locais", status_code=201)
async def criar_local_endpoint(dados: LocalIn):
    """Cria um novo local."""
    if dados.nome in locais:
        raise HTTPException(status_code=400, detail="Local ja existe")
    criar_local(dados.nome, dados.descricao, dados.inventario)
    return local_to_dict(locais[dados.nome])


@app.put("/locais/{nome}")
async def editar_local(nome: str, dados: LocalUpdate):
    """Edita um local existente."""
    loc = locais.get(nome)
    if loc is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado")
    if dados.descricao is not None:
        loc.descricao = dados.descricao
    if dados.inventario is not None:
        loc.inventario = dados.inventario
    return local_to_dict(loc)


@app.delete("/locais/{nome}")
async def remover_local(nome: str):
    """Remove um local do sistema."""
    loc = locais.pop(nome, None)
    if loc is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado")
    # Desassocia agentes que estavam presentes
    for ag in list(loc.agentes_presentes):
        ag.local_atual = None
        loc.remover_agente(ag)
    return {"ok": True}


# ---------------------------- Controle da simulação ---------------------------
@app.post("/ciclo/next")
async def proximo_ciclo():
    """Executa um ciclo para todos os agentes cadastrados."""
    # Antes de iniciar o ciclo, o modulo de RH verifica se deve contratar
    modulo_rh.verificar()
    # Ciclo criativo automatico de ideacao e validacao
    executar_ciclo_criativo()
    resultados = []
    for ag in agentes.values():
        prompt = gerar_prompt_decisao(ag)
        resp = enviar_para_llm(ag, prompt)
        executar_resposta(ag, resp)
        resultados.append(agente_to_dict(ag))
    lucro_info = calcular_lucro_ciclo()
    return {
        "agentes": resultados,
        "saldo": lucro_info["saldo"],
        "historico_saldo": historico_saldo,
        "ideias": [
            {
                "descricao": i.descricao,
                "justificativa": i.justificativa,
                "autor": i.autor,
                "validada": i.validada,
                "executada": i.executada,
                "resultado": i.resultado,
            }
            for i in historico_ideias
        ],
    }

