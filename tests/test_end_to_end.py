from fastapi.testclient import TestClient
import api
import state # Added
# import empresa_digital as ed # No longer needed for direct variable access


def test_startup_creates_company(reset_state):
    """Inicializa a API e verifica se agentes e salas foram criados."""
    with TestClient(api.app) as client:
        agentes = client.get("/agentes").json()
        locais = client.get("/locais").json()
        assert len(agentes) >= 3
        assert len(locais) >= 2
        assert state.historico_saldo  # saldo calculado no startup, check state


def test_multiple_cycles_autonomous(reset_state):
    """Executa múltiplos ciclos e verifica evolução do saldo e ideias."""
    with TestClient(api.app) as client:
        saldos = []
        for _ in range(3):
            resp = client.post("/ciclo/next")
            assert resp.status_code == 200
            saldos.append(resp.json()["saldo"])
        assert len(state.historico_saldo) >= 3 # Check state
        assert state.historico_saldo[-1] >= saldos[0] # Check state
        assert any(i for i in resp.json()["ideias"])
