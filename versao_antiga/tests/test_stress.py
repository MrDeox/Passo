"""Testes de stress simulando grande volume de tarefas."""

import empresa_digital # For functions
import state # Added
import rh


def test_crescimento_rapido_cria_muitos_agentes():
    empresa_digital.criar_local("Lab", "", [])
    for i in range(50):
        empresa_digital.adicionar_tarefa(f"Tarefa {i}")
    state.saldo = 100
    # rh.saldo = state.saldo # rh.py should use state.saldo directly
    rh.modulo_rh.verificar() # rh.py uses state
    # Um agente extra eh criado inicialmente para preencher a sala vazia
    assert len(state.agentes) == 51
    assert not state.tarefas_pendentes # tarefas_pendentes should be empty if all processed


