import logging
import os
from typing import List, Optional, Tuple
from pathlib import Path
import requests

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

ROOT = Path(__file__).parent


class _KeyFile:
    """Wrapper com metodos patchaveis para o arquivo de API key."""

    def __init__(self, path: Path):
        self.path = path

    def exists(self) -> bool:
        return self.path.exists()

    def read_text(self) -> str:
        return self.path.read_text()


KEY_FILE = _KeyFile(ROOT / ".openrouter_key")


def obter_api_key() -> str:
    """Retorna a chave da OpenRouter da variável de ambiente ou arquivo."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    if KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
        os.environ["OPENROUTER_API_KEY"] = key
        return key
    raise RuntimeError("OPENROUTER_API_KEY nao definido")

import state # Added
import empresa_digital # Added
from core_types import Agente, Local # Added
# empresa_digital functions will be used via empresa_digital.func_name
# state variables will be used via state.var_name

from openrouter_utils import (
    buscar_modelos_gratis,
    escolher_modelo_llm,
)
from rh import modulo_rh
from ciclo_criativo import executar_ciclo_criativo # historico_ideias, historico_servicos are now in state
from dataclasses import asdict # To convert Service dataclass to dict

# Configuração de logging global
logging.basicConfig(level=logging.INFO)

# Instância principal da aplicação FastAPI
app = FastAPI(title="Empresa Digital API")

DATA_AGENTES = Path(__file__).parent / "agentes.json"
DATA_LOCAIS = Path(__file__).parent / "locais.json"


@app.on_event("startup")
def _startup() -> None:
    """Inicializa a empresa ou carrega dados persistidos."""
    if (
        "PYTEST_CURRENT_TEST" not in os.environ
        and DATA_AGENTES.exists()
        and DATA_LOCAIS.exists()
    ):
        try:
            empresa_digital.carregar_dados(str(DATA_AGENTES), str(DATA_LOCAIS)) # Use empresa_digital.
            logging.info(
                "Dados carregados de %s e %s", DATA_AGENTES, DATA_LOCAIS
            )
        except Exception as exc:
            logging.error("Falha ao carregar dados: %s", exc)
            empresa_digital.inicializar_automaticamente() # Use empresa_digital.
    else:
        empresa_digital.inicializar_automaticamente() # Use empresa_digital.
    # Dispara automaticamente o primeiro ciclo de simulacao
    state.historico_eventos.clear() # Use state.
    state.registrar_evento("Inicio automatico da empresa") # Use state.
    modulo_rh.verificar()
    executar_ciclo_criativo()
    for ag in list(state.agentes.values()): # Use state.
        prompt = empresa_digital.gerar_prompt_decisao(ag) # Use empresa_digital.
        resp = empresa_digital.enviar_para_llm(ag, prompt) # Use empresa_digital.
        empresa_digital.executar_resposta(ag, resp) # Use empresa_digital.
    empresa_digital.calcular_lucro_ciclo() # Use empresa_digital.


@app.on_event("shutdown")
def _shutdown() -> None:
    """Persiste o estado atual da empresa em disco."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    try:
        empresa_digital.salvar_dados(str(DATA_AGENTES), str(DATA_LOCAIS)) # Use empresa_digital.
        logging.info(
            "Dados salvos em %s e %s", DATA_AGENTES, DATA_LOCAIS
        )
    except Exception as exc:
        logging.error("Erro ao salvar dados: %s", exc)


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


# ---------------------------- Endpoints de agentes ----------------------------

@app.get("/modelos-livres", response_model=List[str])
def modelos_livres_endpoint():
    """Lista todos os modelos gratuitos retornados pela OpenRouter."""
    try:
        return buscar_modelos_gratis()
    except Exception as exc:
        logging.error("Erro ao buscar modelos: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/agentes/escolher-modelo", response_model=ModeloEscolhido)
def escolher_modelo_endpoint(dados: EscolherModeloIn):
    """Determina automaticamente o modelo de LLM para um novo agente."""
    modelos = buscar_modelos_gratis()
    modelo, motivo = escolher_modelo_llm(dados.funcao, "", modelos)
    logging.info("Modelo %s escolhido para %s - %s", modelo, dados.nome, motivo)
    return ModeloEscolhido(modelo=modelo, raciocinio=motivo)

@app.get("/agentes")
async def listar_agentes():
    """Retorna todos os agentes e suas informações."""
    return [agente_to_dict(a) for a in state.agentes.values()] # Use state.


@app.get("/agentes/{nome}")
async def obter_agente(nome: str):
    """Recupera um único agente pelo nome."""
    ag = state.agentes.get(nome) # Use state.
    if ag is None:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")
    return agente_to_dict(ag)


@app.post("/agentes", status_code=201)
async def criar_agente_endpoint(dados: AgentIn):
    """Cria um novo agente."""
    if dados.nome in state.agentes: # Use state.
        raise HTTPException(status_code=400, detail="Agente ja existe")
    empresa_digital.criar_agente( # Use empresa_digital.
        dados.nome,
        dados.funcao,
        dados.modelo_llm,
        dados.local,
        dados.objetivo,
    )
    return agente_to_dict(state.agentes[dados.nome]) # Use state.


@app.put("/agentes/{nome}")
async def editar_agente(nome: str, dados: AgentUpdate):
    """Edita atributos de um agente existente."""
    ag = state.agentes.get(nome) # Use state.
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
        empresa_digital.mover_agente(nome, dados.local) # Use empresa_digital.
    return agente_to_dict(ag)


@app.delete("/agentes/{nome}")
async def remover_agente(nome: str):
    """Remove um agente do sistema."""
    ag = state.agentes.pop(nome, None) # Use state.
    if ag is None:
        raise HTTPException(status_code=404, detail="Agente nao encontrado")
    if ag.local_atual:
        ag.local_atual.remover_agente(ag)
    return {"ok": True}


# ------------------------------ Endpoints locais -----------------------------
@app.get("/locais")
async def listar_locais():
    """Lista todos os locais e quem está em cada um."""
    return [local_to_dict(l) for l in state.locais.values()] # Use state.


@app.get("/locais/{nome}")
async def obter_local(nome: str):
    """Recupera um local específico."""
    loc = state.locais.get(nome) # Use state.
    if loc is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado")
    return local_to_dict(loc)


@app.post("/locais", status_code=201)
async def criar_local_endpoint(dados: LocalIn):
    """Cria um novo local."""
    if dados.nome in state.locais: # Use state.
        raise HTTPException(status_code=400, detail="Local ja existe")
    empresa_digital.criar_local(dados.nome, dados.descricao, dados.inventario) # Use empresa_digital.
    return local_to_dict(state.locais[dados.nome]) # Use state.


@app.put("/locais/{nome}")
async def editar_local(nome: str, dados: LocalUpdate):
    """Edita um local existente."""
    loc = state.locais.get(nome) # Use state.
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
    loc = state.locais.pop(nome, None) # Use state.
    if loc is None:
        raise HTTPException(status_code=404, detail="Local nao encontrado")
    # Desassocia agentes que estavam presentes
    for ag in list(loc.agentes_presentes):
        ag.local_atual = None
        loc.remover_agente(ag)
    return {"ok": True}


# ----------------------------- Eventos em tempo real -------------------------
@app.get("/eventos")
async def listar_eventos():
    """Retorna a lista de eventos registrados no último ciclo."""
    return list(state.historico_eventos) # Use state.


@app.get("/lucro")
async def obter_lucro():
    """Expõe o saldo acumulado e o histórico de lucro."""
    # O `calcular_lucro_ciclo` retorna um dict mais detalhado,
    # mas para este endpoint, manter a resposta simples pode ser ok,
    # ou podemos expandi-la se necessário.
    # Por ora, mantendo simples. O saldo é o mais importante aqui.
    return {"saldo": state.saldo, "historico_saldo": state.historico_saldo} # Use state.


# ------------------------------ Endpoints Serviços -----------------------------
@app.get("/servicos")
async def listar_servicos():
    """Lista todos os serviços propostos e seu estado atual."""
    # historico_servicos is now in state
    # asdict é importado de dataclasses
    return [asdict(s) for s in state.historico_servicos] # Use state.

@app.get("/servicos/{service_id}")
async def obter_servico(service_id: str):
    """Recupera um serviço específico pelo seu ID."""
    servico_encontrado = next((s for s in state.historico_servicos if s.id == service_id), None) # Use state.
    if not servico_encontrado:
        raise HTTPException(status_code=404, detail=f"Serviço com ID '{service_id}' não encontrado.")
    return asdict(servico_encontrado)

# ---------------------------- Controle da simulação ---------------------------
@app.post("/ciclo/next")
async def proximo_ciclo():
    """Executa um ciclo para todos os agentes cadastrados."""
    # Antes de iniciar o ciclo, o modulo de RH verifica se deve contratar
    modulo_rh.verificar()
    # Ciclo criativo automatico de ideacao e validacao
    executar_ciclo_criativo()
    resultados = []
    state.historico_eventos.clear() # Use state.
    for ag in state.agentes.values(): # Use state.
        prompt = empresa_digital.gerar_prompt_decisao(ag) # Use empresa_digital.
        resp = empresa_digital.enviar_para_llm(ag, prompt) # Use empresa_digital.
        empresa_digital.executar_resposta(ag, resp) # Use empresa_digital.
        resultados.append(agente_to_dict(ag))
    lucro_info = empresa_digital.calcular_lucro_ciclo() # Use empresa_digital.
    return {
        "agentes": resultados,
        "saldo": lucro_info["saldo"], # This saldo is from the return value of calcular_lucro_ciclo
        "historico_saldo": state.historico_saldo, # Use state.
        "eventos": list(state.historico_eventos), # Use state.
        "ideias": [asdict(i) for i in state.historico_ideias], # Usar asdict para consistência # Use state.
        "servicos": [asdict(s) for s in state.historico_servicos], # Use state.
    }

