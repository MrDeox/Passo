from fastapi.testclient import TestClient
import api
# import empresa_digital as ed # ed is not used directly in this file


def test_event_endpoint_updates(reset_state):
    """Após um ciclo a API de eventos deve retornar informacoes."""
    client = TestClient(api.app)
    client.post("/locais", json={"nome": "Lab", "descricao": "", "inventario": []})
    client.post(
        "/agentes",
        json={"nome": "A", "funcao": "Ideacao", "modelo_llm": "gpt", "local": "Lab"},
    )
    client.post(
        "/agentes",
        json={"nome": "B", "funcao": "Validador", "modelo_llm": "gpt", "local": "Lab"},
    )
    client.post("/ciclo/next")
    eventos = client.get("/eventos").json()
    assert eventos
