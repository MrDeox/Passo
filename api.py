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
    inicializar_automaticamente,
    carregar_dados,
    salvar_dados,
    historico_eventos,
    registrar_evento,
)
from openrouter_utils import (
    buscar_modelos_gratis,
    escolher_modelo_llm,
)
from rh import modulo_rh
from ciclo_criativo import executar_ciclo_criativo, historico_ideias, historico_servicos # Import historico_servicos
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
            carregar_dados(str(DATA_AGENTES), str(DATA_LOCAIS))
            logging.info(
                "Dados carregados de %s e %s", DATA_AGENTES, DATA_LOCAIS
            )
        except Exception as exc:
            logging.error("Falha ao carregar dados: %s", exc)
            inicializar_automaticamente()
    else:
        inicializar_automaticamente()
    # Dispara automaticamente o primeiro ciclo de simulacao
    historico_eventos.clear()
    registrar_evento("Inicio automatico da empresa")
    modulo_rh.verificar()
    executar_ciclo_criativo()
    for ag in list(agentes.values()):
        prompt = gerar_prompt_decisao(ag)
        resp = enviar_para_llm(ag, prompt)
        executar_resposta(ag, resp)
    calcular_lucro_ciclo()


@app.on_event("shutdown")
def _shutdown() -> None:
    """Persiste o estado atual da empresa em disco."""
    if "PYTEST_CURRENT_TEST" in os.environ:
        return
    try:
        salvar_dados(str(DATA_AGENTES), str(DATA_LOCAIS))
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


# ----------------------------- Eventos em tempo real -------------------------
@app.get("/eventos")
async def listar_eventos():
    """Retorna a lista de eventos registrados no último ciclo."""
    return list(historico_eventos)


@app.get("/lucro")
async def obter_lucro():
    """Expõe o saldo acumulado e o histórico de lucro."""
    # O `calcular_lucro_ciclo` retorna um dict mais detalhado,
    # mas para este endpoint, manter a resposta simples pode ser ok,
    # ou podemos expandi-la se necessário.
    # Por ora, mantendo simples. O saldo é o mais importante aqui.
    return {"saldo": saldo, "historico_saldo": historico_saldo}


# ------------------------------ Endpoints Serviços -----------------------------
@app.get("/servicos")
async def listar_servicos():
    """Lista todos os serviços propostos e seu estado atual."""
    # historico_servicos é importado de ciclo_criativo
    # asdict é importado de dataclasses
    return [asdict(s) for s in historico_servicos]

@app.get("/servicos/{service_id}")
async def obter_servico(service_id: str):
    """Recupera um serviço específico pelo seu ID."""
    servico_encontrado = next((s for s in historico_servicos if s.id == service_id), None)
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
    historico_eventos.clear()
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
        "eventos": list(historico_eventos),
        "ideias": [asdict(i) for i in historico_ideias], # Usar asdict para consistência
        "servicos": [asdict(s) for s in historico_servicos],
    }

