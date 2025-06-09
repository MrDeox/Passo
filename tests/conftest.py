import pytest
import empresa_digital as ed
import rh
from ciclo_criativo import historico_ideias, preferencia_temas

@pytest.fixture(autouse=True)
def reset_state():
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
