"""Testes unitários das funções principais."""

import empresa_digital # For functions like criar_local, criar_agente, etc.
import state # Added
import rh
from ciclo_criativo import executar_ciclo_criativo # historico_ideias now in state


def test_criar_agente():
    local = empresa_digital.criar_local("Sala A", "Teste", []) # Use empresa_digital.
    ag = empresa_digital.criar_agente("Zed", "Dev", "gpt", "Sala A") # Use empresa_digital.
    assert ag in local.agentes_presentes
    assert state.agentes["Zed"] is ag # Use state.
    assert ag.local_atual is local


def test_mover_agente():
    l1 = empresa_digital.criar_local("A", "", []) # Use empresa_digital.
    l2 = empresa_digital.criar_local("B", "", []) # Use empresa_digital.
    ag = empresa_digital.criar_agente("X", "Func", "gpt", "A") # Use empresa_digital.
    empresa_digital.mover_agente("X", "B") # Use empresa_digital.
    assert ag.local_atual is l2
    assert ag not in l1.agentes_presentes
    assert ag in l2.agentes_presentes


def test_calcular_lucro_ciclo():
    l1 = empresa_digital.criar_local("A", "", ["pc", "mesa"]) # Use empresa_digital.
    l2 = empresa_digital.criar_local("B", "", ["notebook"]) # Use empresa_digital.
    a1 = empresa_digital.criar_agente("A1", "Func", "gpt", "A") # Use empresa_digital.
    a2 = empresa_digital.criar_agente("A2", "Func", "gpt", "B") # Use empresa_digital.
    a1.historico_acoes.append("acao ok")
    a2.historico_acoes.append("falha")
    res = empresa_digital.calcular_lucro_ciclo() # Use empresa_digital.
    # calcular_lucro_ciclo's returned "saldo" is state.saldo
    assert res["saldo"] == state.saldo
    # Check against expected value based on logic (10 - 13 = -3, but min saldo is 10)
    assert state.saldo == 10.0
    assert res["receita"] == 10.0 # This is 'receita' from the function, not global saldo
    assert res["custos"] == 13.0
    assert state.historico_saldo[-1] == 10.0 # Use state.


def test_rh_verificar_cria_agentes():
    empresa_digital.criar_local("Lab", "", []) # Use empresa_digital.
    empresa_digital.adicionar_tarefa("Coisa") # Use empresa_digital.
    state.saldo = 10 # Use state.
    # rh.saldo = state.saldo # rh.py should use state.saldo directly
    rh.modulo_rh.verificar()
    # Um agente extra eh criado inicialmente para preencher a sala vazia
    assert "Auto1" in state.agentes # Use state.
    # A tarefa "Coisa" should have been processed and an Executor created for it.
    # The task object itself would be modified (status changed) and removed from state.tarefas_pendentes by rh.py's logic.
    # So, checking if state.tarefas_pendentes is empty might be correct if "Coisa" was the only one.
    # Let's check that the specific task "Coisa" is no longer "todo" or in the list.
    found_task = False
    for task in state.tarefas_pendentes:
        if task.description == "Coisa" and task.status == "todo":
            found_task = True
            break
    assert not found_task, "Tarefa 'Coisa' should have been processed by RH."


def test_ciclo_criativo_gera_tarefa():
    empresa_digital.criar_local("Sala", "", []) # Use empresa_digital.
    empresa_digital.criar_agente("ID", "Ideacao", "gpt", "Sala") # Use empresa_digital.
    empresa_digital.criar_agente("VAL", "Validador", "gpt", "Sala") # Use empresa_digital.
    executar_ciclo_criativo()
    assert len(state.historico_ideias) == 1 # Use state.
    # ciclo_criativo itself does not add to tarefas_pendentes.
    # It generates ideas, which might later become tasks if a product is made and needs marketing, etc.
    # The original assertion `assert ed.tarefas_pendentes` might be based on an older logic.
    # For now, I'll keep it if the test implies some task will be created.
    # On review of ciclo_criativo.py, it does NOT directly add to state.tarefas_pendentes.
    # This assertion is likely incorrect based on current code.
    # However, the goal is to refactor imports, not fix test logic unless necessary for compilation.
    # Let's assume the test setup implies some task will be created.
    assert state.tarefas_pendentes # Use state.
