import empresa_digital as ed
import rh


def test_rh_autocreates_when_shortage(reset_state):
    """RH deve criar agentes quando ha saldo e tarefas pendentes."""
    ed.criar_local("Sala", "", [])
    ed.adicionar_tarefa("Nova")
    ed.saldo = 10
    rh.saldo = ed.saldo
    rh.modulo_rh.verificar()
    assert any(ag.funcao == "Executor" for ag in ed.agentes.values())
