import pytest
import os
import json
from unittest.mock import patch, mock_open, call # mock_open for file operations
import shutil # For cleaning up test directories/files

import empresa_digital # Changed ed to empresa_digital
import state # Added
import config # Added
from core_types import Task, Service, Ideia # For creating test data and type checks
import ciclo_criativo as cc # For accessing its history lists directly in assertions
# Note: cc.historico_ideias will become state.historico_ideias in assertions below.
import rh # For modulo_rh

# Define a temporary directory for test save files
TEST_SAVE_DIR = "test_save_data_temp"

# Standard filenames used by the simulation
SAVE_FILES = {
    "agentes": os.path.join(TEST_SAVE_DIR, "agentes_estado.json"),
    "locais": os.path.join(TEST_SAVE_DIR, "locais_estado.json"),
    "ideias": os.path.join(TEST_SAVE_DIR, "historico_ideias.json"),
    "servicos": os.path.join(TEST_SAVE_DIR, "servicos.json"),
    "saldo": os.path.join(TEST_SAVE_DIR, "saldo.json"),
    "tarefas": os.path.join(TEST_SAVE_DIR, "tarefas.json"),
    "eventos": os.path.join(TEST_SAVE_DIR, "eventos.json"),
}

@pytest.fixture(autouse=True)
def setup_teardown_test_dir():
    # Create temp dir before each test
    if os.path.exists(TEST_SAVE_DIR):
        shutil.rmtree(TEST_SAVE_DIR) # Clean up from previous failed run if any
    os.makedirs(TEST_SAVE_DIR, exist_ok=True)

    # Reset global state of ed and cc modules before each test
    state.agentes.clear()
    state.locais.clear()
    state.tarefas_pendentes.clear()
    state.historico_eventos.clear()
    state.saldo = 0.0
    state.historico_saldo.clear()
    state.ciclo_atual_simulacao = 0 # Reset cycle count
    state.historico_ideias.clear() # Changed from cc.historico_ideias
    state.historico_servicos.clear() # Changed from cc.historico_servicos
    state.preferencia_temas.clear() # Changed from cc.preferencia_temas

    yield # This is where the test runs

    # Cleanup after each test
    if os.path.exists(TEST_SAVE_DIR):
        shutil.rmtree(TEST_SAVE_DIR)


class TestPersistence:
    def test_save_and_load_all_data_structures(self):
        # 1. Setup initial state
        empresa_digital.inicializar_automaticamente() # Creates some default agents, locals, one task
        state.saldo = 1234.56
        state.historico_saldo.append(1000.0)
        state.historico_saldo.append(state.saldo)

        # Add a service
        servico1 = Service(service_name="Serviço Teste Persist", description="D", author="Aut")
        state.historico_servicos.append(servico1)

        # Add another task (Task object)
        task_obj = empresa_digital.adicionar_tarefa("Tarefa Persistente Complexa")
        task_obj.update_status("in_progress", "Iniciada para teste")

        # Add an idea
        ideia1 = Ideia(descricao="Ideia Persistente", justificativa="J", autor="Au")
        state.historico_ideias.append(ideia1)

        state.registrar_evento("Evento de teste para persistência.")

        # Capture state before saving (or parts of it for comparison)
        original_num_agentes = len(state.agentes)
        original_num_locais = len(state.locais)
        original_num_tarefas = len(state.tarefas_pendentes)
        original_task_desc = task_obj.description
        original_task_status = task_obj.status
        original_num_eventos = len(state.historico_eventos)
        original_num_servicos = len(state.historico_servicos)
        original_num_ideias = len(state.historico_ideias)

        # 2. Save data
        empresa_digital.salvar_dados(
            SAVE_FILES["agentes"], SAVE_FILES["locais"],
            SAVE_FILES["ideias"], SAVE_FILES["servicos"],
            SAVE_FILES["saldo"], SAVE_FILES["tarefas"], SAVE_FILES["eventos"]
        )

        # 3. Reset state (as if starting a new session)
        state.agentes.clear()
        state.locais.clear()
        state.tarefas_pendentes.clear()
        state.historico_eventos.clear()
        state.saldo = 0.0
        state.historico_saldo.clear()
        state.historico_ideias.clear()
        state.historico_servicos.clear()

        # 4. Load data
        empresa_digital.carregar_dados(
            SAVE_FILES["agentes"], SAVE_FILES["locais"],
            SAVE_FILES["ideias"], SAVE_FILES["servicos"],
            SAVE_FILES["saldo"], SAVE_FILES["tarefas"], SAVE_FILES["eventos"]
        )

        # 5. Assertions
        assert state.saldo == 1234.56
        assert state.historico_saldo == [1000.0, 1234.56]

        assert len(state.agentes) == original_num_agentes
        assert len(state.locais) == original_num_locais

        assert len(state.tarefas_pendentes) == original_num_tarefas
        loaded_task = next((t for t in state.tarefas_pendentes if t.description == original_task_desc), None)
        assert loaded_task is not None
        assert loaded_task.status == original_task_status
        assert len(loaded_task.history) > 0 # Check if history was persisted (Task.update_status adds to it)

        assert len(state.historico_eventos) == original_num_eventos
        assert "Evento de teste para persistência." in state.historico_eventos

        assert len(state.historico_servicos) == original_num_servicos
        assert state.historico_servicos[0].service_name == "Serviço Teste Persist"

        assert len(state.historico_ideias) == original_num_ideias
        assert state.historico_ideias[0].descricao == "Ideia Persistente"

    def test_load_backward_compatibility_for_string_tasks(self):
        # Create a dummy tarefas.json with old string format
        old_format_tasks = ["Tarefa antiga 1", "Outra tarefa de string"]
        with open(SAVE_FILES["tarefas"], "w", encoding="utf-8") as f:
            json.dump(old_format_tasks, f)

        # Ensure other files are not there or are empty to isolate task loading
        for key, path in SAVE_FILES.items():
            if key != "tarefas" and os.path.exists(path):
                os.remove(path) # Or write empty json list/dict

        empresa_digital.carregar_dados(
            SAVE_FILES["agentes"], SAVE_FILES["locais"],
            SAVE_FILES["ideias"], SAVE_FILES["servicos"],
            SAVE_FILES["saldo"], SAVE_FILES["tarefas"], SAVE_FILES["eventos"]
        )

        assert len(state.tarefas_pendentes) == 2
        assert isinstance(state.tarefas_pendentes[0], Task)
        assert state.tarefas_pendentes[0].description == "Tarefa antiga 1"
        assert state.tarefas_pendentes[0].status == "todo"
        assert isinstance(state.tarefas_pendentes[1], Task)
        assert state.tarefas_pendentes[1].description == "Outra tarefa de string"
        assert state.tarefas_pendentes[1].status == "todo"

        event_conversion_found = any("Tarefa antiga 'Tarefa antiga 1' convertida" in evento for evento in state.historico_eventos)
        assert event_conversion_found


class TestRunSimulationEntryPoint:
    @patch('empresa_digital.executar_um_ciclo_completo')
    def test_run_finite_cycles(self, mock_executar_ciclo):
        mock_executar_ciclo.return_value = True # Simulate successful cycles
        num_test_cycles = 3

        empresa_digital.run_simulation_entry_point(num_cycles=num_test_cycles, resume_flag=False)

        assert mock_executar_ciclo.call_count == num_test_cycles
        # ciclo_atual_simulacao is updated by executar_um_ciclo_completo which updates state.ciclo_atual_simulacao
        assert state.ciclo_atual_simulacao == num_test_cycles
        assert state.MODO_VIDA_INFINITA is False # run_simulation_entry_point sets this in state

    @patch('empresa_digital.executar_um_ciclo_completo')
    @patch('empresa_digital.salvar_dados') # To check if it's called on interrupt
    def test_run_infinite_cycles_keyboard_interrupt(self, mock_salvar_dados, mock_executar_ciclo):
        # Simulate KeyboardInterrupt after a few cycles
        num_cycles_before_interrupt = 2

        def side_effect_executar_ciclo(ciclo_num):
            if ciclo_num > num_cycles_before_interrupt:
                raise KeyboardInterrupt("Simulated Ctrl-C")
            return True
        mock_executar_ciclo.side_effect = side_effect_executar_ciclo

        with pytest.raises(SystemExit) as pytest_wrapped_e: # run_simulation_entry_point calls sys.exit
             empresa_digital.run_simulation_entry_point(num_cycles=0, resume_flag=False)

        assert pytest_wrapped_e.type == SystemExit
        assert pytest_wrapped_e.value.code == 0

        assert mock_executar_ciclo.call_count == num_cycles_before_interrupt + 1 # It's called, then raises
        assert state.MODO_VIDA_INFINITA is True # run_simulation_entry_point sets this in state
        mock_salvar_dados.assert_called_once() # Ensure data is saved on interrupt

    @patch('empresa_digital.inicializar_automaticamente')
    @patch('empresa_digital.carregar_dados')
    @patch('empresa_digital.executar_um_ciclo_completo')
    def test_resume_functionality(self, mock_executar_ciclo, mock_carregar_dados, mock_inicializar):
        mock_executar_ciclo.return_value = True

        # Test with resume=True
        empresa_digital.run_simulation_entry_point(num_cycles=1, resume_flag=True)
        mock_carregar_dados.assert_called_once()
        mock_inicializar.assert_not_called() # Should not init if resume is attempted

        mock_carregar_dados.reset_mock()
        mock_inicializar.reset_mock()

        # Test with resume=False
        empresa_digital.run_simulation_entry_point(num_cycles=1, resume_flag=False)
        mock_carregar_dados.assert_not_called()
        mock_inicializar.assert_called_once()

    @patch('empresa_digital.carregar_dados', side_effect=FileNotFoundError("Simulated missing save files"))
    @patch('empresa_digital.inicializar_automaticamente')
    @patch('empresa_digital.executar_um_ciclo_completo')
    def test_resume_failing_loads_starts_new(self, mock_executar_ciclo, mock_inicializar, mock_carregar_dados):
        mock_executar_ciclo.return_value = True

        empresa_digital.run_simulation_entry_point(num_cycles=1, resume_flag=True)

        mock_carregar_dados.assert_called_once()
        mock_inicializar.assert_called_once() # Should initialize if loading fails


if __name__ == "__main__":
    pytest.main()
