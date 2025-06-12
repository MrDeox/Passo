"""Testes de integração simulando um ciclo completo."""

from unittest.mock import patch, MagicMock
import json # Necessário para criar o mock da resposta JSON
import empresa_digital # Changed ed to empresa_digital
import state # Added
import rh
from ciclo_criativo import executar_ciclo_criativo
# Import Ideia from core_types if needed for test_ideia instance
from core_types import Ideia


@patch('empresa_digital.obter_api_key', return_value="fake_api_key") # Mock API key globally for this test
@patch('requests.post') # Mock requests.post globally for this test
def test_ciclo_completo_altera_saldo(mock_post, mock_obter_key, reset_state): # Added reset_state fixture
    # Configurar o mock para requests.post para retornar uma resposta padrão
    # Isso garante que os agentes executem uma ação (ex: "ficar")
    mock_response = MagicMock()
    mock_response.status_code = 200
    # Usar uma ação simples e válida para todos os agentes neste teste de integração
    # O conteúdo exato da ação pode não ser crítico, desde que seja válido
    action_content = {"acao": "ficar"}
    mock_response.json.return_value = {"choices": [{"message": {"content": json.dumps(action_content)}}]}
    mock_response.text = json.dumps({"choices": [{"message": {"content": json.dumps(action_content)}}]})
    mock_post.return_value = mock_response

    # Configura dois locais e agentes basicos
    empresa_digital.criar_local("Tecnologia", "", ["pc"])
    empresa_digital.criar_local("Reuniao", "", [])

    alice = empresa_digital.criar_agente("Alice", "Ideacao", "gpt-test", "Tecnologia")
    bob = empresa_digital.criar_agente("Bob", "Validador", "gpt-test", "Reuniao")

    # Tarefa inicial para acionar o RH
    empresa_digital.adicionar_tarefa("Inicial")
    state.saldo = 20
    rh.modulo_rh.verificar() # Isso pode criar "Auto1"

    # Ciclo criativo gera nova tarefa
    executar_ciclo_criativo()

    # Assegurar que todos os agentes tenham histórico de ações para cálculo de lucro
    alice.historico_acoes.append("dummy action ok")

    # Executa decisoes para cada agente
    for ag_nome in list(state.agentes.keys()):
        ag = state.agentes[ag_nome]
        prompt = empresa_digital.gerar_prompt_decisao(ag)
        resp = empresa_digital.enviar_para_llm(ag, prompt)
        empresa_digital.executar_resposta(ag, resp)

    result = empresa_digital.calcular_lucro_ciclo()

    assert "Auto1" in state.agentes, "RH deveria ter contratado Auto1"
    assert result["saldo"] == 34.0, f"Saldo calculado incorretamente. Detalhes: {result}"
    assert state.historico_saldo[-1] == 34.0
    assert state.tarefas_pendentes # tarefa gerada pelo ciclo criativo


@patch('ciclo_criativo.sugerir_conteudo_marketing')
@patch('ciclo_criativo.produto_digital')
@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post')
def test_product_creation_and_marketing_flow(
    mock_requests_post,
    mock_obter_key,
    mock_produto_digital,
    mock_sugerir_marketing,
    reset_state
):
    # --- Setup ---
    mock_gumroad_url = "https://gum.co/testprod123"
    mock_produto_digital.return_value = mock_gumroad_url
    mock_sugerir_marketing.return_value = "Marketing content here!"

    test_ideia = Ideia(
        descricao="Produto Teste para Fluxo Completo",
        justificativa="Testar a integração da criação e marketing.",
        autor="Teste Integrado",
        validada=True,
        link_produto=None
    )

    # Mock ciclo_criativo.propor_ideias to make it use our test_ideia.
    # propor_ideias directly appends to state.historico_ideias.
    # We want prototipar_ideias to pick up this specific idea.
    # So, instead of mocking propor_ideias, we can manually add to state.historico_ideias
    # and ensure validar_propostas (if it runs on it) keeps it validated.
    state.historico_ideias.append(test_ideia)
    # If validar_propostas is called, ensure it doesn't invalidate our test_ideia.
    # For simplicity, assume it will be processed as is by prototipar_ideias.

    # --- Execution ---
    empresa_digital.criar_local("TestLocal", "Local de teste", [])
    empresa_digital.criar_agente("TestAgenteCriador", "CriadorDeProdutos", "test-model", "TestLocal")
    empresa_digital.criar_agente("TestAgenteDivulgador", "Divulgador", "test-model", "TestLocal")

    mock_llm_response = MagicMock()
    mock_llm_response.status_code = 200
    action_content = {"acao": "ficar"}
    mock_llm_response.json.return_value = {"choices": [{"message": {"content": json.dumps(action_content)}}]}
    mock_llm_response.text = json.dumps({"choices": [{"message": {"content": json.dumps(action_content)}}]})
    mock_requests_post.return_value = mock_llm_response

    executar_ciclo_criativo() # This will call prototipar_ideias internally

    # --- Assertions ---
    mock_produto_digital.assert_called_once()
    called_ideia_pd, _, _ = mock_produto_digital.call_args[0]
    assert called_ideia_pd.descricao == test_ideia.descricao

    assert len(state.historico_ideias) > 0, "state.historico_ideias should not be empty"
    processed_ideia = None
    for idea_in_history in state.historico_ideias:
        if idea_in_history.descricao == test_ideia.descricao:
            processed_ideia = idea_in_history
            break

    assert processed_ideia is not None, "Test idea not found in state.historico_ideias"
    assert processed_ideia.link_produto == mock_gumroad_url, "link_produto was not set on the idea"

    mock_sugerir_marketing.assert_called_once()
    called_ideia_sm, called_url_sm = mock_sugerir_marketing.call_args[0]
    assert called_ideia_sm.descricao == test_ideia.descricao
    assert called_url_sm == mock_gumroad_url

    all_events_string = " | ".join(state.historico_eventos) # Use state
    assert f"Novo produto '{test_ideia.descricao}' criado e publicado na Gumroad: {mock_gumroad_url}" in all_events_string
    assert f"Geradas sugestões de marketing para o produto: {test_ideia.descricao}" in all_events_string

# Note: The import `from ciclo_criativo import Ideia` might cause issues if `empresa_digital.py`
# also imports `Ideia` from `ciclo_criativo.py` at the top level, leading to circular dependencies.
# A common solution is to define `Ideia` in a separate `models.py` or ensure imports are carefully managed.
# For this test, `ed.Ideia` is used assuming `empresa_digital` imports `Ideia` successfully.
# Also, `ed.cc.historico_ideias` assumes `ciclo_criativo` is imported as `cc` in `empresa_digital` or
# that `historico_ideias` is directly accessible.
# Let's assume `import ciclo_criativo as cc` is added to `empresa_digital.py` or that `historico_ideias` is
# directly available from `ciclo_criativo` module itself for the assertion.
# The test uses `ed.cc.historico_ideias` which implies `empresa_digital` has `import ciclo_criativo as cc`.
# If not, it should be `import ciclo_criativo; ciclo_criativo.historico_ideias`.
# For simplicity, I'll assume `ciclo_criativo.historico_ideias` is directly accessible.
# The previous change to empresa_digital.py added `from ciclo_criativo import Ideia, ...`
# but not `import ciclo_criativo as cc`. So direct access to `ciclo_criativo.historico_ideias` is needed.
# I'll adjust the assertion to use `import ciclo_criativo` and then `ciclo_criativo.historico_ideias`.
# Actually, since `reset_state` clears `ciclo_criativo.historico_ideias`, we can check it directly.
# `reset_state` is defined in `conftest.py` and should handle clearing relevant global states.
# The test flow of `executar_ciclo_criativo` populates `ciclo_criativo.historico_ideias`.
# So, the assertion `assert len(ciclo_criativo.historico_ideias) > 0` and subsequent checks are fine.
# The `ed.Ideia` needs `from ciclo_criativo import Ideia` in `empresa_digital.py` for it to work.
# This was part of a previous step.
# Final check of historico_eventos: `ed.historico_eventos` is correct.
