"""Testes de stress simulando grande volume de tarefas."""

import empresa_digital as ed
import rh


def test_crescimento_rapido_cria_muitos_agentes():
    ed.criar_local("Lab", "", [])
    for i in range(50):
        ed.adicionar_tarefa(f"Tarefa {i}")
    ed.saldo = 100
    rh.saldo = ed.saldo
    rh.modulo_rh.verificar()
    # Um agente extra eh criado inicialmente para preencher a sala vazia
    assert len(ed.agentes) == 51
    assert not ed.tarefas_pendentes


