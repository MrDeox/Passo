import empresa_digital as ed


def test_auto_initialization_creates_resources(reset_state):
    """Verifica se a inicialização automática gera salas, agentes e tarefas."""
    ed.inicializar_automaticamente()
    assert ed.locais
    assert ed.agentes
    assert ed.tarefas_pendentes


def test_model_selection_heuristics():
    """Garante que a escolha do modelo LLM segue a heurística esperada."""
    assert ed.selecionar_modelo("Dev")[0] == "deepseek-chat"
    assert ed.selecionar_modelo("CEO")[0] == "phi-4:free"
    assert ed.selecionar_modelo("Outro")[0] == "gpt-3.5-turbo"
