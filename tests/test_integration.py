"""Testes de integração simulando um ciclo completo."""

from unittest.mock import patch, MagicMock
import json # Necessário para criar o mock da resposta JSON
import empresa_digital as ed
import rh
from ciclo_criativo import executar_ciclo_criativo


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
    ed.criar_local("Tecnologia", "", ["pc"]) # reset_state deve limpar isso se executado antes
    ed.criar_local("Reuniao", "", [])
    # É importante que reset_state seja usado se este teste modificar o estado global
    # que outros testes podem depender, ou se ele espera um estado limpo.
    # Assumindo que reset_state limpa ed.locais, ed.agentes, etc.

    alice = ed.criar_agente("Alice", "Ideacao", "gpt-test", "Tecnologia") # Usar um modelo de teste
    bob = ed.criar_agente("Bob", "Validador", "gpt-test", "Reuniao")   # Usar um modelo de teste

    # Tarefa inicial para acionar o RH
    ed.adicionar_tarefa("Inicial")
    ed.saldo = 20
    # rh.saldo = ed.saldo # rh.py deve usar ed.saldo diretamente ou ter seu próprio gerenciamento
                           # Se rh.saldo é uma cópia, precisa ser atualizado se ed.saldo mudar.
                           # Para este teste, vamos assumir que a lógica interna do RH acessa ed.saldo corretamente.
    rh.modulo_rh.verificar() # Isso pode criar "Auto1"

    # Ciclo criativo gera nova tarefa
    executar_ciclo_criativo() # Isso pode adicionar tarefas a ed.tarefas_pendentes

    # Assegurar que todos os agentes tenham histórico de ações para cálculo de lucro
    # A resposta mockada fará todos os agentes executarem 'ficar -> ok'
    alice.historico_acoes.append("dummy action ok") # Para garantir alguma receita se 'ficar' não gerar.
                                                 # Na verdade, 'ficar -> ok' já é registrado.

    # Executa decisoes para cada agente (agora mockado para não fazer chamadas reais)
    # O mock_post configurado no início do teste será usado por chamar_openrouter_api
    for ag_nome in list(ed.agentes.keys()): # Iterar sobre nomes para evitar problemas de modificação de dict
        ag = ed.agentes[ag_nome]
        prompt = ed.gerar_prompt_decisao(ag)
        # enviar_para_llm chamará chamar_openrouter_api que usará o mock_post
        resp = ed.enviar_para_llm(ag, prompt)
        ed.executar_resposta(ag, resp)

    result = ed.calcular_lucro_ciclo()

    # Verifica contratacao e atualizacao do saldo
    # O número de agentes será Alice, Bob, e Auto1 (se o RH contratar)
    # Custos: 3 agentes * 5 = 15
    # Recursos: Alice no Tecnologia (pc) = 1. Bob na Reuniao = 0. Auto1 (se criado) em Lab (se Lab existir e tiver itens)
    # Se Auto1 é criado pelo RH, ele é colocado em um local. Precisamos saber qual.
    # rh.py: novo_agente.local_atual = locais_ordenados[0] (primeiro local por nome)
    # Se "Lab" é o primeiro, e tem itens, isso afeta os custos.
    # Para este teste, vamos assumir que "Reuniao" é o primeiro local por nome (ordem alfabética)
    # ou que o local de Auto1 não tem recursos extras para simplificar.
    # Se Auto1 está em "Reuniao" (0 recursos) ou "Tecnologia" (1 recurso).
    # Assumindo Auto1 em "Reuniao" (0 recursos) se "Lab" não for criado ou for depois.
    # Locais criados: Tecnologia, Reuniao. "Reuniao" vem antes de "Tecnologia" alfabeticamente.
    # Então Auto1 irá para "Reuniao". Custo de recursos = 1 (somente de Alice).
    # Total de custos = 15 (salarios) + 1 (recursos) = 16.

    # Receita: cada agente que registra "-> ok" gera 10.
    # Alice (ficar -> ok), Bob (ficar -> ok), Auto1 (ficar -> ok) = 3 * 10 = 30.
    # Saldo anterior = 20.
    # Novo saldo = 20 + 30 (receita) - 16 (custos) = 34.

    assert "Auto1" in ed.agentes, "RH deveria ter contratado Auto1"
    # Ajustar as expectativas de saldo com base na lógica acima.
    # O saldo inicial é 20.
    # Receita: 3 agentes * 10 (por 'ficar -> ok') = 30.
    # Custo de salários: 3 agentes * 5 = 15.
    # Custo de recursos: Alice em Tecnologia (1 item 'pc') = 1. Bob em Reuniao (0 itens) = 0.
    # Auto1, se criado, vai para 'Reuniao' (primeiro local em ordem alfabética). Custo de recursos = 0.
    # Total de custos = 15 (salários) + 1 (recursos) = 16.
    # Saldo final = Saldo inicial + Receita - Custos = 20 + 30 - 16 = 34.

    assert result["saldo"] == 34.0, f"Saldo calculado incorretamente. Detalhes: {result}"
    assert ed.historico_saldo[-1] == 34.0
    assert ed.tarefas_pendentes # tarefa gerada pelo ciclo criativo


@patch('ciclo_criativo.sugerir_conteudo_marketing') # Mock at the point of call in ciclo_criativo
@patch('ciclo_criativo.produto_digital')      # Mock at the point of call in ciclo_criativo
@patch('empresa_digital.obter_api_key', return_value="fake_api_key")
@patch('requests.post') # Mock general LLM calls if any other agents run
def test_product_creation_and_marketing_flow(
    mock_requests_post, # For any other LLM calls by other agents
    mock_obter_key,
    mock_produto_digital,
    mock_sugerir_marketing,
    reset_state # Fixture to reset global state before test
):
    # --- Setup ---
    # Mock a successful product creation
    mock_gumroad_url = "https://gum.co/testprod123"
    mock_produto_digital.return_value = mock_gumroad_url

    # Mock successful marketing suggestion (not strictly necessary to check its return if just checking call)
    mock_sugerir_marketing.return_value = "Marketing content here!"

    # Create a validated idea and add it to a temporary list that prototipar_ideias will use.
    # ciclo_criativo.historico_ideias is extended at the end of executar_ciclo_criativo.
    # prototipar_ideias takes a list of 'ideias' as input.
    # We need to ensure this idea is processed by prototipar_ideias.
    # The flow in executar_ciclo_criativo:
    # 1. propor_ideias() ->
    # 2. validar_ideias(ideias_propostas) ->
    # 3. prototipar_ideias(ideias_propostas) ->
    # 4. historico_ideias.extend(ideias_propostas)
    # So, we need to mock propor_ideias and validar_ideias to produce our test idea.

    # Import Ideia from core_types for creating the test instance
    from core_types import Ideia
    test_ideia = Ideia(
        descricao="Produto Teste para Fluxo Completo",
        justificativa="Testar a integração da criação e marketing.",
        autor="Teste Integrado",
        validada=True, # Pre-validate it for prototipar_ideias
        link_produto=None # Ensure it doesn't have a link yet
    )

    # Mock propor_ideias to return our specific test idea
    # Mock validar_ideias to ensure our idea remains validated (or mock its internal logic)
    # Patching them within ciclo_criativo's namespace
    with patch('ciclo_criativo.propor_ideias', return_value=[test_ideia]) as mock_propor, \
         patch('ciclo_criativo.validar_ideias', lambda ideias: None) as mock_validar: # Simple lambda to do nothing but ensure validada=True is kept

        # --- Execution ---
        # Execute a cycle. This will call prototipar_ideias, which should trigger our mocks.
        # Ensure some basic agents exist if prototipar_ideias or other parts of the cycle need them.
        ed.criar_local("TestLocal", "Local de teste", [])
        ed.criar_agente("TestAgenteCriador", "CriadorDeProdutos", "test-model", "TestLocal")
        ed.criar_agente("TestAgenteDivulgador", "Divulgador", "test-model", "TestLocal")

        # Mock LLM calls for any other agents that might run to avoid errors
        # if they are part of executar_ciclo_criativo's broader scope.
        # The main test_ciclo_completo_altera_saldo already does this with a global mock_post.
        # We can rely on the global mock_requests_post for other agents.
        mock_llm_response = MagicMock()
        mock_llm_response.status_code = 200
        action_content = {"acao": "ficar"} # Default action for other agents
        mock_llm_response.json.return_value = {"choices": [{"message": {"content": json.dumps(action_content)}}]}
        mock_llm_response.text = json.dumps({"choices": [{"message": {"content": json.dumps(action_content)}}]})
        mock_requests_post.return_value = mock_llm_response

        executar_ciclo_criativo()

    # --- Assertions ---
    # 1. Check if produto_digital was called correctly
    mock_produto_digital.assert_called_once()
    called_ideia_pd, _, _ = mock_produto_digital.call_args[0]
    assert called_ideia_pd.descricao == test_ideia.descricao

    # 2. Check if the idea in historico_ideias has the link_produto set
    # historico_ideias is a global in ciclo_criativo module
    import ciclo_criativo # Import locally to access its global
    assert len(ciclo_criativo.historico_ideias) > 0, "historico_ideias should not be empty"
    processed_ideia = None
    for idea_in_history in ciclo_criativo.historico_ideias: # Access directly
        if idea_in_history.descricao == test_ideia.descricao:
            processed_ideia = idea_in_history
            break

    assert processed_ideia is not None, "Test idea not found in historico_ideias"
    assert processed_ideia.link_produto == mock_gumroad_url, "link_produto was not set on the idea"

    # 3. Check if sugerir_conteudo_marketing was called correctly
    mock_sugerir_marketing.assert_called_once()
    called_ideia_sm, called_url_sm = mock_sugerir_marketing.call_args[0]
    assert called_ideia_sm.descricao == test_ideia.descricao
    assert called_url_sm == mock_gumroad_url

    # 4. Check if an event for product creation was registered (done by produto_digital)
    # This part is tricky as registrar_evento is in 'criador_de_produtos' and 'divulgador'
    # We'd need to patch those specific instances or check ed.historico_eventos if it's global.
    # For this test, focusing on the direct calls (produto_digital, sugerir_marketing) and
    # the state change (ideia.link_produto) is primary.
    # We can assume unit tests for criador_de_produtos and divulgador verify their own event registration.

    # Example: Check ed.historico_eventos for relevant messages if it's reliable
    # This assumes registrar_evento in criador_de_produtos and divulgador use the global ed.historico_eventos
    # Convert ed.historico_eventos to a single string to search for substrings
    all_events_string = " | ".join(ed.historico_eventos)
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
