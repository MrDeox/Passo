import pytest
import empresa_digital as ed # Still needed for monkeypatching functions in ed
import rh
# from ciclo_criativo import historico_ideias, preferencia_temas # Moved to state
import state # Added

@pytest.fixture(autouse=True)
def reset_state(monkeypatch):
    """Limpa variáveis globais antes e depois de cada teste."""
    state.MODO_VIDA_INFINITA = False
    state.agentes.clear()
    state.locais.clear()
    state.tarefas_pendentes.clear()
    state.historico_saldo.clear()
    state.saldo = 0.0
    state.historico_ideias.clear()
    state.preferencia_temas.clear()
    rh.modulo_rh._contador = 1
    # rh.saldo = state.saldo # If rh.py is updated to use state.saldo directly, this line is not needed.
                           # For now, assuming rh.saldo might still exist as a separate variable in rh.py
                           # that was intended to mirror ed.saldo. This might need further review.
                           # Given rh.py was updated to use state.saldo, this line is likely not necessary.
                           # However, to be safe for this step, I'll keep it if rh.saldo exists as a module var.
                           # On review of rh.py changes, rh.saldo is not a separate variable.
                           # So, this line can be removed.
    monkeypatch.setattr(
        "openrouter_utils.buscar_modelos_gratis",
        lambda: ["gpt-3.5-turbo"],
    )
    monkeypatch.setattr(
        "openrouter_utils.obter_api_key",
        lambda: "dummy",
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
    monkeypatch.setattr(ed, "obter_api_key", lambda: "dummy")
    yield
    state.agentes.clear()
    state.locais.clear()
    state.tarefas_pendentes.clear()
    state.historico_saldo.clear()
    state.saldo = 0.0
    state.historico_ideias.clear()
    state.preferencia_temas.clear()
    rh.modulo_rh._contador = 1
    # rh.saldo = state.saldo # See comment above, removing this.
    state.MODO_VIDA_INFINITA = False
