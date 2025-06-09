from fastapi.testclient import TestClient
import api
import empresa_digital as ed

client = TestClient(api.app)


def test_crud_endpoints(reset_state):
    # cria local
    resp = client.post(
        "/locais",
        json={"nome": "Lab", "descricao": "Sala de testes", "inventario": ["pc"]},
    )
    assert resp.status_code == 201
    assert resp.json()["nome"] == "Lab"

    # cria agente associado ao local
    resp = client.post(
        "/agentes",
        json={
            "nome": "Zed",
            "funcao": "Dev",
            "modelo_llm": "gpt",
            "local": "Lab",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["local_atual"] == "Lab"

    # lista agentes
    resp = client.get("/agentes")
    assert any(a["nome"] == "Zed" for a in resp.json())

    # atualiza agente
    resp = client.put("/agentes/Zed", json={"funcao": "QA"})
    assert resp.status_code == 200
    assert resp.json()["funcao"] == "QA"

    # edita local
    resp = client.put(
        "/locais/Lab",
        json={"descricao": "Atualizada", "inventario": ["pc", "mesa"]},
    )
    assert resp.json()["descricao"] == "Atualizada"
    assert resp.json()["inventario"] == ["pc", "mesa"]

    # remove agente
    resp = client.delete("/agentes/Zed")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert client.get("/agentes").json() == []

    # remove local
    resp = client.delete("/locais/Lab")
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}
    assert client.get("/locais").json() == []


def test_ciclo_next(reset_state):
    client.post(
        "/locais",
        json={"nome": "Lab", "descricao": "desc", "inventario": []},
    )
    client.post(
        "/agentes",
        json={"nome": "Alice", "funcao": "Ideacao", "modelo_llm": "gpt", "local": "Lab"},
    )
    client.post(
        "/agentes",
        json={"nome": "Bob", "funcao": "Validador", "modelo_llm": "gpt", "local": "Lab"},
    )

    resp = client.post("/ciclo/next")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["agentes"]) == 2
    assert data["saldo"] == -10.0
    assert ed.historico_saldo[-1] == -10.0
    assert data["ideias"]
