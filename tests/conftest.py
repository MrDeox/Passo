import pytest
import empresa_digital as ed
import rh
from ciclo_criativo import historico_ideias, preferencia_temas

@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    """Limpa variáveis globais antes e depois de cada teste."""
    ed.agentes.clear()
    ed.locais.clear()
    ed.tarefas_pendentes.clear()
    ed.historico_saldo.clear()
    ed.saldo = 0.0
    historico_ideias.clear()
    preferencia_temas.clear()
    rh.modulo_rh._contador = 1
    rh.saldo = ed.saldo
    monkeypatch.setattr(
        "openrouter_utils.buscar_modelos_gratis",
        lambda: ["gpt-3.5-turbo"],
    )
    monkeypatch.setattr(
        "openrouter_utils.escolher_modelo_llm",
        lambda funcao, objetivo, modelos: (modelos[0], "mock"),
    )
    monkeypatch.setattr(
        ed, "buscar_modelos_gratis", lambda: ["gpt-3.5-turbo"]
    )
    monkeypatch.setattr(
        ed, "escolher_modelo_llm", lambda funcao, objetivo, modelos: (modelos[0], "mock")
    )
    yield
    ed.agentes.clear()
    ed.locais.clear()
    ed.tarefas_pendentes.clear()
    ed.historico_saldo.clear()
    ed.saldo = 0.0
    historico_ideias.clear()
    preferencia_temas.clear()
    rh.modulo_rh._contador = 1
    rh.saldo = ed.saldo
