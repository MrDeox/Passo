import os
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

import api # Importa o módulo api para testar obter_api_key
import empresa_digital as ed

client = TestClient(api.app)


# Testes para api.obter_api_key()

@patch.dict(os.environ, {"OPENROUTER_API_KEY": "env_key_123"}, clear=True)
def test_obter_api_key_from_env():
    """Testa se a API key é obtida corretamente da variável de ambiente."""
    assert api.obter_api_key() == "env_key_123"

@patch.dict(os.environ, {}, clear=True) # Garante que OPENROUTER_API_KEY não está no os.environ
@patch('api.KEY_FILE.exists', return_value=True)
@patch('api.KEY_FILE.read_text', return_value=" file_key_456 \n") # Testar com espaço e newline
def test_obter_api_key_from_file(mock_read_text, mock_exists):
    """Testa se a API key é obtida do arquivo .openrouter_key se não estiver no env."""
    key = api.obter_api_key()
    assert key == "file_key_456"
    # Verifica também se a chave lida do arquivo é colocada no os.environ
    assert os.environ["OPENROUTER_API_KEY"] == "file_key_456"

@patch.dict(os.environ, {}, clear=True)
@patch('api.KEY_FILE.exists', return_value=False)
def test_obter_api_key_not_found(mock_exists):
    """Testa se RuntimeError é levantado quando a chave não é encontrada."""
    with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY nao definido"):
        api.obter_api_key()

# Teste para o caso de a chave estar no arquivo e também no ambiente (ambiente deve ter precedência)
@patch.dict(os.environ, {"OPENROUTER_API_KEY": "env_key_789"}, clear=True)
@patch('api.KEY_FILE.exists', return_value=True)
@patch('api.KEY_FILE.read_text', return_value="file_key_should_be_ignored")
def test_obter_api_key_env_takes_precedence(mock_read_text, mock_exists):
    """Testa se a chave do ambiente tem precedência sobre a do arquivo."""
    assert api.obter_api_key() == "env_key_789"
    mock_exists.assert_not_called() # Não deve nem checar o arquivo se a chave está no env
    mock_read_text.assert_not_called()


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
