import empresa_digital as ed


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
