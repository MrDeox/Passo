from fastapi.testclient import TestClient
import api
import empresa_digital as ed


def test_startup_creates_company(reset_state):
    """Inicializa a API e verifica se agentes e salas foram criados."""
    with TestClient(api.app) as client:
        agentes = client.get("/agentes").json()
        locais = client.get("/locais").json()
        assert len(agentes) >= 3
        assert len(locais) >= 2
        assert ed.historico_saldo  # saldo calculado no startup


def test_multiple_cycles_autonomous(reset_state):
    """Executa múltiplos ciclos e verifica evolução do saldo e ideias."""
    with TestClient(api.app) as client:
        saldos = []
        for _ in range(3):
            resp = client.post("/ciclo/next")
            assert resp.status_code == 200
            saldos.append(resp.json()["saldo"])
        assert len(ed.historico_saldo) >= 3
        assert saldos[-1] != saldos[0]
        assert any(i for i in resp.json()["ideias"])
