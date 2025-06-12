import pytest # For fixtures like reset_state if it's from pytest
import empresa_digital # For functions
import state # Added
import config # Added (though MODO_VIDA_INFINITA is read from state for runtime changes)
import rh
from core_types import Task # To manually add Task objects if needed for setup
from unittest.mock import patch
import random # To control random.random() for layoff/redefine tests

# Assuming reset_state is a fixture that clears ed.agentes, ed.locais, ed.tarefas_pendentes, ed.saldo etc.
# If not, we might need to define it or do manual setup/teardown.
# For now, assuming reset_state correctly resets the global state in empresa_digital.

def test_rh_autocreates_executor_for_task(reset_state): # Renamed for clarity
    """RH deve criar um Executor quando há saldo e uma tarefa 'todo' pendente."""
    empresa_digital.criar_local("Sala Comum", "Local para agentes", [])
    # empresa_digital.adicionar_tarefa now creates Task objects.
    # The original test for adicionar_tarefa implies it adds to state.tarefas_pendentes
    task = empresa_digital.adicionar_tarefa("Resolver problema X")
    assert task in state.tarefas_pendentes
    assert task.status == "todo"

    state.saldo = 50 # Suficiente para contratar
    # rh.saldo = state.saldo # rh.py directly uses state.saldo now

    rh.modulo_rh.verificar() # rh.py uses state

    assert len(state.agentes) > 0, "Nenhum agente foi criado pelo RH."

    created_executor = next((ag for ag in state.agentes.values() if ag.funcao == "Executor"), None)
    assert created_executor is not None, "Nenhum Executor foi criado."
    assert created_executor.objetivo_atual == f"task_id:{task.id}", "Executor não foi atribuído à tarefa corretamente."
    assert task.status == "in_progress", "Status da tarefa não foi atualizado para 'in_progress'."
    # Check if the task was removed from 'todo' list effectively (it's status changed)
    # The original check `assert state.tarefas_pendentes == []` might be too strict if other tasks could exist.
    # Instead, check that this specific task is no longer "todo" or is handled.
    # Since `verificar` pops tasks, it shouldn't be in tarefas_pendentes if processed.
    assert task not in state.tarefas_pendentes, "Tarefa processada não foi removida da lista de pendências do RH."


class TestExecutorIdleLogic:

    def test_executor_cycles_idle_increment(self, reset_state):
        local = empresa_digital.criar_local("Escritorio", "Local de trabalho", [])
        executor = empresa_digital.criar_agente("ExecutorOcioso", "Executor", "gpt-4", local.nome, objetivo_atual="Aguardando novas atribuições.")
        assert executor.cycles_idle == 0

        rh.modulo_rh.verificar() # Ciclo 1 de ociosidade
        assert executor.cycles_idle == 1, "Ciclo de ociosidade não incrementado para Executor ocioso."

        rh.modulo_rh.verificar() # Ciclo 2 de ociosidade
        assert executor.cycles_idle == 2

        # Dar um objetivo ao executor
        executor.objetivo_atual = "task_id:xyz123"
        rh.modulo_rh.verificar() # Ciclo com objetivo
        assert executor.cycles_idle == 0, "Ciclo de ociosidade não foi resetado após receber um objetivo."

    @patch('random.random')
    def test_executor_dismissal_after_5_idle_cycles(self, mock_random, reset_state):
        mock_random.return_value = 0.4 # Garante a decisão de dispensar (0.4 < 0.5)

        local = empresa_digital.criar_local("SalaDispensa", "Local de teste", [])
        executor_name = "ExecutorParaDispensar"
        executor = empresa_digital.criar_agente(executor_name, "Executor", "gpt-4", local.nome, objetivo_atual="Aguardando novas atribuições.")
        executor.cycles_idle = 4 # Prepara para atingir 5 no próximo ciclo

        rh.modulo_rh.verificar() # Ciclo 5 -> dispensa

        assert executor_name not in state.agentes, f"Executor {executor_name} não foi dispensado." # Use state
        assert executor not in local.agentes_presentes, f"Executor {executor_name} não foi removido do local."

        # Verificar evento de dispensa
        dispensa_event_found = any(
            f"Executor {executor_name} removido do sistema por ociosidade" in evento
            for evento in state.historico_eventos # Use state
        )
        assert dispensa_event_found, "Evento de dispensa do Executor não registrado."

    @patch('random.random')
    def test_executor_role_change_after_5_idle_cycles(self, mock_random, reset_state):
        mock_random.return_value = 0.6 # Garante a decisão de redefinir (0.6 >= 0.5)

        local = empresa_digital.criar_local("SalaRedefinicao", "Local de teste", [])
        executor_name = "ExecutorParaRedefinir"
        executor = empresa_digital.criar_agente(executor_name, "Executor", "gpt-4", local.nome, objetivo_atual="Aguardando novas atribuições.")
        executor.cycles_idle = 4

        rh.modulo_rh.verificar() # Ciclo 5 -> redefinição

        assert executor_name in state.agentes, "Executor foi removido em vez de redefinido." # Use state
        redefined_agent = state.agentes[executor_name] # Use state
        assert redefined_agent.funcao == "Funcionario", "Função do Executor não foi redefinida para 'Funcionario'."
        assert redefined_agent.objetivo_atual == "Aguardando novas diretrizes como Funcionario."
        assert redefined_agent.cycles_idle == 0, "Contador de ociosidade não foi resetado após redefinição."

        redefine_event_found = any(
            f"Executor {executor_name} redefinido para 'Funcionario' por ociosidade" in evento
            for evento in state.historico_eventos # Use state
        )
        assert redefine_event_found, "Evento de redefinição de função do Executor não registrado."

    def test_non_executor_not_affected_by_idle_logic(self, reset_state):
        local = empresa_digital.criar_local("SalaNormal", "Local de trabalho", [])
        ceo_agent = empresa_digital.criar_agente("Chefe", "CEO", "gpt-4", local.nome, objetivo_atual="Aguardando novas atribuições.")
        ceo_agent.cycles_idle = 10 # Simula ociosidade alta

        rh.modulo_rh.verificar()

        assert "Chefe" in state.agentes # Não deve ser demitido # Use state
        assert ceo_agent.funcao == "CEO" # Função não deve mudar
        assert ceo_agent.cycles_idle == 10 # Contador não deve ser gerenciado para não-Executores por esta lógica específica
                                         # (A lógica de incremento só afeta Executores)

    def test_executor_with_valid_objective_not_laid_off(self, reset_state):
        local = empresa_digital.criar_local("SalaTrabalho", "Local de trabalho", [])
        task_id = "task_abc"
        executor = empresa_digital.criar_agente("ExecutorOcupado", "Executor", "gpt-4", local.nome, objetivo_atual=f"task_id:{task_id}")
        executor.cycles_idle = 10 # Simula ociosidade prévia alta, mas agora tem objetivo

        rh.modulo_rh.verificar() # Ciclo onde ele tem um objetivo

        assert "ExecutorOcupado" in state.agentes # Use state
        assert executor.cycles_idle == 0 # Deve ser resetado
        assert executor.funcao == "Executor"
