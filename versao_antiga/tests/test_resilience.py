from fastapi.testclient import TestClient
import api
# import empresa_digital as ed # Not directly used
# import ciclo_criativo # Not directly used
import pytest


def test_modelos_livres_error_logging(monkeypatch):
    """Simula falha ao buscar modelos e checa se a API responde com erro."""
    def fail(*_, **__):
        raise RuntimeError("falha")
    monkeypatch.setattr(
        api, "buscar_modelos_gratis", fail, raising=False
    )
    client = TestClient(api.app)
    resp = client.get("/modelos-livres")
    assert resp.status_code == 500


def test_ciclo_next_failure(monkeypatch, reset_state):
    """Se algum passo falha, a API deve retornar erro ao usuario."""
    def fail(*_, **__):
        raise RuntimeError("error")
    # Patching diretamente a funcao importada pelo modulo da API
    monkeypatch.setattr(api, "executar_ciclo_criativo", fail)
    client = TestClient(api.app, raise_server_exceptions=False)
    resp = client.post("/ciclo/next")
    assert resp.status_code == 500

