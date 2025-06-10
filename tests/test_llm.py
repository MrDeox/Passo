import json
import time # Adicionado para mockar time.sleep e testar delays
from unittest.mock import patch, MagicMock, call # call para verificar chamadas a sleep
import pytest # pytest é usado para fixtures como reset_state, mas patch é do unittest.mock
import requests.exceptions

import empresa_digital as ed
from empresa_digital import Agente, Local, OPENROUTER_CALL_DELAY_SECONDS # Importar classes e a constante de delay

# Helper para criar um agente simples para testes
def criar_agente_teste(nome="TestAgente", modelo="test-model"):
    # Certifique-se de que um local padrão exista ou crie um temporário se necessário
    if "DefaultLocal" not in ed.locais:
        ed.criar_local("DefaultLocal", "Local padrão para testes")
    return ed.criar_agente(nome, "Tester", modelo, "DefaultLocal", "Test objective")

def test_auto_initialization_creates_resources(reset_state):
    """Verifica se a inicialização automática gera salas, agentes e tarefas."""
    ed.inicializar_automaticamente()
    assert ed.locais
    assert ed.agentes
    assert ed.tarefas_pendentes


def test_model_selection_does_not_fail():
    """Verifica se a selecao de modelo retorna um resultado e justificativa."""
    modelo, rac = ed.selecionar_modelo("Dev")
    assert modelo
    assert rac

def test_model_selection_heuristics():
    """Garante que a escolha do modelo LLM segue a heurística esperada."""
    assert ed.selecionar_modelo("Dev")[0] == "deepseek-chat"
    assert ed.selecionar_modelo("CEO")[0] == "phi-4:free"
    assert ed.selecionar_modelo("Outro")[0] == "gpt-3.5-turbo"


# Testes para chamar_openrouter_api
@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
@patch('time.sleep', autospec=True) # Mock time.sleep
@patch('empresa_digital.OPENROUTER_CALL_DELAY_SECONDS', 0) # Set delay to 0 for this test
def test_chamar_openrouter_api_success_first_attempt(mock_sleep, mock_post, mock_obter_key, reset_state):
    """Test successful API call on the first attempt without retries."""
    agente = criar_agente_teste()
    prompt = "Test prompt"

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"choices": [{"message": {"content": '{"acao": "ficar"}'}}]}
    mock_response.text = json.dumps({"choices": [{"message": {"content": '{"acao": "ficar"}'}}]})
    mock_post.return_value = mock_response

    result = ed.chamar_openrouter_api(agente, prompt)

    mock_post.assert_called_once()
    # Assert that the initial delay sleep (which is 0 here due to patch) was called,
    # but no other sleeps for backoff occurred.
    mock_sleep.assert_called_once_with(0) # OPENROUTER_CALL_DELAY_SECONDS is patched to 0
    assert result == '{"acao": "ficar"}'
    mock_obter_key.assert_called_once()

@patch('empresa_digital.obter_api_key', return_value=None)
@patch('requests.post') # Need to patch requests.post to check it's NOT called
def test_chamar_openrouter_api_no_key(mock_post, mock_obter_key, reset_state): # mock_post added
    agente = criar_agente_teste()
    prompt = "Test prompt"

    result = ed.chamar_openrouter_api(agente, prompt)

    expected_error = {"error": "API key not found", "details": "OpenRouter API key is missing or not configured."}
    assert json.loads(result) == expected_error
    mock_obter_key.assert_called_once()
    mock_post.assert_not_called() # Verify that requests.post was not called

@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
@patch('time.sleep', autospec=True)
@patch('empresa_digital.OPENROUTER_CALL_DELAY_SECONDS', 0) # Disable fixed delay for this test
def test_chamar_openrouter_api_timeout_with_retry_success(mock_time_sleep, mock_requests_post, mock_obter_key, reset_state):
    """Test that a Timeout exception triggers a retry and can succeed."""
    agente = criar_agente_teste()
    prompt = "Test prompt for timeout retry"

    successful_response = MagicMock()
    successful_response.status_code = 200
    successful_response.json.return_value = {"choices": [{"message": {"content": '{"acao": "timeout_success"}'}}]}
    successful_response.text = json.dumps(successful_response.json.return_value)

    # First call raises Timeout, second call is successful
    mock_requests_post.side_effect = [
        requests.exceptions.Timeout("API timed out on first attempt"),
        successful_response
    ]

    result = ed.chamar_openrouter_api(agente, prompt)

    assert mock_requests_post.call_count == 2
    # First call to sleep is the OPENROUTER_CALL_DELAY_SECONDS (0), second is the backoff
    expected_sleep_calls = [
        call(0),  # Initial delay from OPENROUTER_CALL_DELAY_SECONDS = 0
        call(1)   # INITIAL_BACKOFF_DELAY = 1 second for the first retry
    ]
    mock_time_sleep.assert_has_calls(expected_sleep_calls)

    assert result == '{"acao": "timeout_success"}'
    mock_obter_key.assert_called_once() # API key should still be obtained only once


@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
@patch('time.sleep', autospec=True)
@patch('empresa_digital.OPENROUTER_CALL_DELAY_SECONDS', 0)
def test_chamar_openrouter_api_retry_on_specific_codes_then_success(mock_time_sleep, mock_requests_post, mock_obter_key, reset_state):
    """Test retry on specified error codes (429) and eventual success."""
    agente = criar_agente_teste()
    prompt = "Test prompt for 429 retry"

    error_response_429 = MagicMock()
    error_response_429.status_code = 429
    error_response_429.text = '{"error": "Too Many Requests"}'

    successful_response = MagicMock()
    successful_response.status_code = 200
    successful_response.json.return_value = {"choices": [{"message": {"content": '{"acao": "retry_success"}'}}]}
    successful_response.text = json.dumps(successful_response.json.return_value)

    mock_requests_post.side_effect = [error_response_429, successful_response]

    result = ed.chamar_openrouter_api(agente, prompt)

    assert mock_requests_post.call_count == 2
    expected_sleep_calls = [call(0), call(1)] # Initial delay (0) + 1s backoff
    mock_time_sleep.assert_has_calls(expected_sleep_calls)
    assert result == '{"acao": "retry_success"}'
    mock_obter_key.assert_called_once()


@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
@patch('time.sleep', autospec=True)
@patch('empresa_digital.OPENROUTER_CALL_DELAY_SECONDS', 0)
def test_chamar_openrouter_api_exhaust_retries(mock_time_sleep, mock_requests_post, mock_obter_key, reset_state):
    """Test that API call fails after exhausting all retries on a retryable error."""
    agente = criar_agente_teste()
    prompt = "Test prompt for exhausting retries"

    error_response_500 = MagicMock()
    error_response_500.status_code = 500
    error_response_500.text = '{"error": "Internal Server Error"}'
    # raise_for_status for 500 should be implicitly handled if not 200 or other retryable
    # however, our code explicitly checks for retryable status codes.

    mock_requests_post.side_effect = [error_response_500, error_response_500, error_response_500] # MAX_RETRIES = 3

    result = ed.chamar_openrouter_api(agente, prompt)

    assert mock_requests_post.call_count == 3 # Called MAX_RETRIES times
    expected_sleep_calls = [
        call(0),  # Initial delay (0)
        call(1),  # 1st backoff: 1 * (2**0) = 1s
        call(2)   # 2nd backoff: 1 * (2**1) = 2s
    ]
    mock_time_sleep.assert_has_calls(expected_sleep_calls)

    expected_error_payload = {"error": "Erro na API OpenRouter: 500", "details": '{"error": "Internal Server Error"}'}
    assert json.loads(result) == expected_error_payload
    mock_obter_key.assert_called_once()


@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
@patch('time.sleep', autospec=True)
@patch('empresa_digital.OPENROUTER_CALL_DELAY_SECONDS', 0)
def test_chamar_openrouter_api_no_retry_on_non_retryable_code(mock_time_sleep, mock_requests_post, mock_obter_key, reset_state):
    """Test that non-retryable error codes (e.g., 400) are not retried."""
    agente = criar_agente_teste()
    prompt = "Test prompt for non-retryable error"

    error_response_400 = MagicMock()
    error_response_400.status_code = 400
    error_response_400.text = '{"error": "Bad Request"}'
    # For non-retryable client errors that are not 429, raise_for_status() would typically be called.
    # Our function calls it if status is not 200 and not in RETRYABLE_STATUS_CODES.
    error_response_400.raise_for_status.side_effect = requests.exceptions.HTTPError("Bad Request")
    mock_requests_post.return_value = error_response_400

    result = ed.chamar_openrouter_api(agente, prompt)

    mock_requests_post.assert_called_once()
    # Only the initial delay sleep should be called
    mock_time_sleep.assert_called_once_with(0)

    # The error is caught by the generic RequestException handler after raise_for_status
    expected_error_payload = {"error": "API call failed", "details": "Bad Request"}
    assert json.loads(result) == expected_error_payload
    mock_obter_key.assert_called_once()


@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
@patch('time.sleep', autospec=True)
def test_chamar_openrouter_api_fixed_call_delay_applied(mock_time_sleep, mock_requests_post, mock_obter_key, reset_state):
    """Test that OPENROUTER_CALL_DELAY_SECONDS is applied."""
    # Temporarily set the delay to a non-zero value for this test
    with patch('empresa_digital.OPENROUTER_CALL_DELAY_SECONDS', 0.1):
        agente = criar_agente_teste()
        prompt = "Test prompt for fixed delay"

        successful_response = MagicMock()
        successful_response.status_code = 200
        successful_response.json.return_value = {"choices": [{"message": {"content": '{"acao": "delay_test_success"}'}}]}
        successful_response.text = json.dumps(successful_response.json.return_value)
        mock_requests_post.return_value = successful_response

        result = ed.chamar_openrouter_api(agente, prompt)

        mock_requests_post.assert_called_once()
        # The first call to sleep should be the fixed delay
        mock_time_sleep.assert_called_once_with(0.1)
        assert result == '{"acao": "delay_test_success"}'
        mock_obter_key.assert_called_once()


@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
def test_chamar_openrouter_api_invalid_json_response(mock_requests_post, mock_obter_key, reset_state):
    # This test is largely the same, but ensure it doesn't conflict with retry logic for sleep calls
    # by also patching OPENROUTER_CALL_DELAY_SECONDS to 0 and time.sleep.
    with patch('time.sleep', autospec=True) as mock_time_sleep, \
         patch('empresa_digital.OPENROUTER_CALL_DELAY_SECONDS', 0):
        agente = criar_agente_teste()
        prompt = "Test prompt"

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "Esto no es JSON"
        mock_response.json.side_effect = json.JSONDecodeError("Error", "doc", 0)
        mock_requests_post.return_value = mock_response

        result = ed.chamar_openrouter_api(agente, prompt)

        expected_error = {"error": "API call failed", "details": "Invalid JSON response from API."}
        assert json.loads(result) == expected_error
        mock_time_sleep.assert_called_once_with(0) # Ensure initial delay sleep was called

@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
def test_chamar_openrouter_api_unexpected_structure(mock_requests_post, mock_obter_key, reset_state):
    # Similar to above, ensure this test is also robust to sleep calls by patching them.
    with patch('time.sleep', autospec=True) as mock_time_sleep, \
         patch('empresa_digital.OPENROUTER_CALL_DELAY_SECONDS', 0):
        agente = criar_agente_teste()
        prompt = "Test prompt"

        mock_response = MagicMock()
        mock_response.status_code = 200
        # Resposta com estrutura inesperada (e.g. faltando 'message')
        unexpected_payload = {"choices": [{"something_else": {"content": '{"acao": "ficar"}'}}]}
        mock_response.json.return_value = unexpected_payload
        mock_response.text = json.dumps(unexpected_payload)
        mock_requests_post.return_value = mock_response

        result = ed.chamar_openrouter_api(agente, prompt)

        loaded_result = json.loads(result)
        assert loaded_result["error"] == "Invalid response structure"
        mock_time_sleep.assert_called_once_with(0) # Ensure initial delay sleep was called
    # O detalhe da exceção pode variar, então verificamos apenas a chave de erro principal

@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
# Patched time.sleep and OPENROUTER_CALL_DELAY_SECONDS as this is a non-retryable error test
@patch('time.sleep', autospec=True)
@patch('empresa_digital.OPENROUTER_CALL_DELAY_SECONDS', 0)
def test_chamar_openrouter_api_http_error_non_retryable_401(mock_time_sleep, mock_requests_post, mock_obter_key, reset_state):
    """ Test a specific non-retryable HTTP error like 401. """
    agente = criar_agente_teste()
    prompt = "Test prompt for 401 error"

    mock_response = MagicMock()
    mock_response.status_code = 401 # Unauthorized - non-retryable
    mock_response.text = '{"error": "Unauthorized key"}'
    mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("Unauthorized key")
    mock_requests_post.return_value = mock_response

    result = ed.chamar_openrouter_api(agente, prompt)

    mock_requests_post.assert_called_once()
    mock_time_sleep.assert_called_once_with(0) # Only initial delay sleep

    loaded_result = json.loads(result)
    assert loaded_result["error"] == "API call failed" # This is the generic wrapper for RequestException
    assert "Unauthorized key" in loaded_result["details"]


# Testes para enviar_para_llm
@patch('empresa_digital.chamar_openrouter_api')
def test_enviar_para_llm_calls_chamar_openrouter_api(mock_chamar_api, reset_state):
    agente = criar_agente_teste()
    prompt = "Test prompt for enviar_para_llm"
    mock_chamar_api.return_value = '{"acao": "ficar"}' # Simula uma resposta bem sucedida

    response = ed.enviar_para_llm(agente, prompt)

    mock_chamar_api.assert_called_once_with(agente, prompt)
    assert response == '{"acao": "ficar"}'


# Testes para executar_resposta
# Usar pytest.mark.parametrize para testar múltiplos cenários para executar_resposta
@pytest.mark.parametrize("resposta_llm, expected_action_details, fallback_involved", [
    # Casos de sucesso
    ('{"acao": "ficar"}', "ficar -> ok", False),
    ('{"acao": "mover", "local": "SalaNova"}', "mover para SalaNova -> ok", False),
    ('{"acao": "mensagem", "destinatario": "Bob", "texto": "Ola"}', "mensagem para Bob -> ok", False),
    # Casos de erro da API (já tratados e retornam JSON de erro)
    ('{"error": "API call failed", "details": "Request timed out."}', "API call error -> falha", True),
    ('{"error": "Invalid response structure", "details": "..."}', "API call error -> falha", True), # Detalhe pode variar
    # Casos de JSON inválido
    ("not a json", "invalid JSON response -> falha", True), # Fallback para ficar deve ser registrado como ok
    # Casos de ação inválida/ausente
    ('{"action": "errada"}', "acao invalida 'None' -> falha", True), # 'acao' não 'action'. Fallback para ficar.
    ('{"acao": "unknown_action"}', "acao invalida 'unknown_action' -> falha", True), # Fallback para ficar.
    ('{}', "acao invalida 'None' -> falha", True), # JSON Vazio. Fallback para ficar.
    # Casos de parâmetros inválidos para ações (devem aplicar fallback para 'ficar')
    ('{"acao": "mover", "lcal": "SalaNova"}', "mover para 'None' -> falha (destino invalido)", True), # 'local' typo, an actual 'None' is passed as destination
    ('{"acao": "mover", "local": "NaoExiste"}', "mover para NaoExiste -> falha (local nao existe)", True),
    ('{"acao": "mensagem", "destinatario": "NaoExisteBob", "texto": "Ola"}', "mensagem para NaoExisteBob -> falha (destinatario nao existe)", True),
    ('{"acao": "mensagem", "destinatario": "Bob"}', "mensagem para Bob -> falha (dados invalidos)", True), # Texto ausente
])
def test_executar_resposta_scenarios(reset_state, resposta_llm, expected_action_details, fallback_involved):
    # Criar locais e agentes necessários para os testes
    ed.criar_local("SalaNova", "Sala de teste para mover")
    agente_principal = criar_agente_teste(nome="Principal")
    ed.criar_agente("Bob", "colega", "test-model", "DefaultLocal")

    # Limpar histórico de ações para isolar o teste
    agente_principal.historico_acoes.clear()

    ed.executar_resposta(agente_principal, resposta_llm)

    assert len(agente_principal.historico_acoes) > 0, f"Nenhuma ação registrada para resposta: {resposta_llm}"
    last_action = agente_principal.historico_acoes[-1]

    if "API call error" in expected_action_details and "API call error" in last_action:
        assert "API call error -> falha" == last_action
    elif fallback_involved:
        # Se um fallback ocorreu, a ação registrada pode ser "ficar (fallback ...) -> ok"
        # ou a falha original seguida por um "ficar" se a lógica for complexa.
        # O mais importante é que o agente não quebre e registre algo.
        # A lógica atual de executar_resposta para JSON inválido ou ação inválida
        # diretamente executa e registra o fallback "ficar (...) -> ok".
        # Check if the primary expected failure was registered (it might not be the *last* action if a fallback occurred)
        # For robustness, we check if any registered action contains the expected detail of the initial failure.
        action_history_str = " | ".join(agente_principal.historico_acoes)
        assert expected_action_details in action_history_str, \
            f"Expected initial failure '{expected_action_details}' not found in action history: '{action_history_str}' for response '{resposta_llm}'"

        # Then, specifically check the *last* action is a successful fallback "ficar" action
        if "API call error" not in last_action : # API call errors don't have a 'ficar' fallback in the current code
            assert "ficar (fallback" in last_action and last_action.endswith("-> ok"), \
                f"Last action for '{resposta_llm}' was expected to be a successful 'ficar' fallback, but got '{last_action}'"
        else: # For "API call error", the error itself is the last action
            assert expected_action_details == last_action

    else: # Not fallback_involved (direct success)
        assert last_action == expected_action_details

# Teste específico para quando `obter_api_key` em si falha (e.g., lança exceção)
# Embora `chamar_openrouter_api` atualmente capture `obter_api_key` retornando None,
# testar o comportamento se `obter_api_key` lançasse uma exceção pode ser útil
# se `obter_api_key` fosse mais complexo.
# @patch('empresa_digital.obter_api_key', side_effect=RuntimeError("Falha ao ler chave"))
# def test_chamar_openrouter_api_obter_key_exception(mock_obter_key, reset_state):
#     agente = criar_agente_teste()
#     prompt = "Test prompt"
#     # Este teste depende de como você quer que chamar_openrouter_api lide com exceções de obter_api_key.
#     # Atualmente, ele não tem um try-except em volta de obter_api_key().
#     # Se tivesse, poderíamos testar o retorno de um JSON de erro.
#     # Como não tem, a exceção RuntimeError propagaria, o que é um comportamento aceitável.
#     with pytest.raises(RuntimeError, match="Falha ao ler chave"):
#         ed.chamar_openrouter_api(agente, prompt)
#     mock_obter_key.assert_called_once()

# Adicionar mais testes para cobrir outros cenários se necessário.
# Por exemplo, testar `executar_resposta` com diferentes tipos de mensagens,
# locais com nomes complexos, etc.
# Também seria bom testar o estado emocional do agente após ações com sucesso/falha.

# Nota sobre `reset_state`: Assume-se que é uma fixture (e.g. de conftest.py)
# que limpa o estado global (agentes, locais, etc.) antes de cada teste.
# Exemplo de fixture `reset_state` em conftest.py:
# @pytest.fixture
# def reset_state():
#     ed.agentes.clear()
#     ed.locais.clear()
#     ed.historico_eventos.clear()
#     ed.tarefas_pendentes.clear()
#     ed.saldo = 0.0
#     ed.historico_saldo.clear()
#     # Recriar quaisquer locais/agentes padrão se necessário para todos os testes
#     yield
#     # Limpeza pós-teste se necessário
#     ed.agentes.clear()
#     ed.locais.clear()
#     # ... etc.

