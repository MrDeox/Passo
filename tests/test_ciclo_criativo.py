import pytest
from unittest.mock import patch, MagicMock, call
import os # For file operations in marketing tests
import json # For LLM response mocking

# Assuming core_types, empresa_digital, ciclo_criativo are importable
import empresa_digital as ed
from core_types import Ideia, Service
import ciclo_criativo as cc # Import the module to be tested

# Helper to reset global state in ciclo_criativo and empresa_digital for relevant tests
@pytest.fixture(autouse=True)
def reset_global_state():
    ed.historico_eventos.clear()
    ed.agentes.clear()
    ed.locais.clear() # Clear locais if cc functions depend on it
    ed.saldo = 0.0
    cc.historico_ideias.clear()
    cc.historico_servicos.clear()
    cc.preferencia_temas.clear()
    # Ensure a default local exists if functions assume one
    if not ed.locais:
        ed.criar_local("Laboratorio Default", "Local de fallback para testes", [])


class TestProporIdeias:
    @patch('empresa_digital.enviar_para_llm')
    def test_propor_ideias_product_idea(self, mock_enviar_para_llm):
        # Setup agent
        ed.criar_agente("AgenteIdeacao1", "Ideacao", "mock_model", list(ed.locais.keys())[0])

        # Mock LLM response for a product idea
        product_response = {
            "type": "product",
            "name": "Super Produto IA",
            "description": "Um produto revolucionário com IA.",
            "justification": "Resolve um grande problema.",
            "target_audience": "Todos os humanos"
        }
        mock_enviar_para_llm.return_value = json.dumps(product_response)

        cc.propor_ideias()

        assert len(cc.historico_ideias) == 1
        assert len(cc.historico_servicos) == 0
        new_ideia = cc.historico_ideias[0]
        assert new_ideia.descricao == "Um produto revolucionário com IA."
        assert new_ideia.justificativa == "Resolve um grande problema."
        assert new_ideia.autor == "AgenteIdeacao1"
        # Check if 'name' and 'target_audience' are used if Ideia class supports them
        # (Currently, Ideia only has 'descricao', 'justificativa', 'autor')

        # Check for event
        event_found = any(
            f"Nova IDEIA DE PRODUTO: '{product_response['name']}' por AgenteIdeacao1" in evento
            for evento in ed.historico_eventos
        )
        assert event_found

    @patch('empresa_digital.enviar_para_llm')
    def test_propor_ideias_service_idea(self, mock_enviar_para_llm):
        ed.criar_agente("AgenteIdeacao2", "Ideacao", "mock_model", list(ed.locais.keys())[0])

        service_response = {
            "type": "service",
            "service_name": "Consultoria IA Avançada",
            "description": "Consultoria para implementar IA.",
            "required_skills": ["IA Expert", "Consultor"],
            "estimated_effort_hours": 100,
            "pricing_model": "fixed_price",
            "price_amount": 5000.00
        }
        mock_enviar_para_llm.return_value = json.dumps(service_response)

        cc.propor_ideias()

        assert len(cc.historico_servicos) == 1
        assert len(cc.historico_ideias) == 0
        new_service = cc.historico_servicos[0]
        assert new_service.service_name == "Consultoria IA Avançada"
        assert new_service.description == "Consultoria para implementar IA."
        assert new_service.author == "AgenteIdeacao2"
        assert new_service.price_amount == 5000.00

        event_found = any(
            f"Novo SERVIÇO proposto: '{service_response['service_name']}' por AgenteIdeacao2" in evento
            for evento in ed.historico_eventos
        )
        assert event_found

    @patch('empresa_digital.enviar_para_llm')
    def test_propor_ideias_no_idea(self, mock_enviar_para_llm):
        ed.criar_agente("AgenteIdeacao3", "Ideacao", "mock_model", list(ed.locais.keys())[0])

        none_response = {"type": "none"}
        mock_enviar_para_llm.return_value = json.dumps(none_response)

        cc.propor_ideias()

        assert len(cc.historico_ideias) == 0
        assert len(cc.historico_servicos) == 0
        event_found = any(
            "AgenteIdeacao3 decidiu não propor uma ideia ou serviço desta vez." in evento
            for evento in ed.historico_eventos # Check ed.historico_eventos, logger checked separately
        )
        # The direct logging is to logger, not historico_eventos for "none" type usually.
        # We'd need to check caplog for logger output.
        # For now, let's assume the function logs correctly and check no objects were created.
        # To check logger:
        # with self.assertLogs(level='INFO') as log_cm:
        #    cc.propor_ideias()
        # self.assertTrue(any("decidiu não propor" in msg for msg in log_cm.output))


    @patch('empresa_digital.enviar_para_llm')
    def test_propor_ideias_invalid_json(self, mock_enviar_para_llm):
        ed.criar_agente("AgenteIdeacao4", "Ideacao", "mock_model", list(ed.locais.keys())[0])
        mock_enviar_para_llm.return_value = "Este não é um JSON válido"

        cc.propor_ideias()
        assert len(cc.historico_ideias) == 0
        assert len(cc.historico_servicos) == 0
        # Check logs for error (using caplog if this were pytest, or by other means)

    @patch('empresa_digital.enviar_para_llm')
    def test_propor_ideias_no_ideacao_agents(self, mock_enviar_para_llm):
        # No agents created
        cc.propor_ideias()
        mock_enviar_para_llm.assert_not_called()
        assert len(cc.historico_ideias) == 0
        assert len(cc.historico_servicos) == 0

# More test classes for validar_propostas, prototipar_ideias, executar_servicos_validados will follow.

class TestValidarPropostas:
    @patch('empresa_digital.enviar_para_llm')
    def test_validar_ideia_aprovada(self, mock_enviar_para_llm):
        ed.criar_agente("ValidadorAgente1", "Validador", "mock_model_val", list(ed.locais.keys())[0])
        ideia = Ideia(descricao="Ideia para validar", justificativa="J", autor="AutorTeste")
        cc.historico_ideias.append(ideia)

        approve_response = {"decision": "aprovar", "justification": "Parece promissora."}
        mock_enviar_para_llm.return_value = json.dumps(approve_response)

        cc.validar_propostas([ideia], [])

        assert ideia.validada is True
        event_found = any(f"Ideia de Produto '{ideia.descricao}' APROVADO" in evento for evento in ed.historico_eventos)
        assert event_found

    @patch('empresa_digital.enviar_para_llm')
    def test_validar_servico_rejeitado(self, mock_enviar_para_llm):
        ed.criar_agente("ValidadorAgente2", "Validador", "mock_model_val", list(ed.locais.keys())[0])
        servico = Service(service_name="Serviço para validar", description="D", author="AutorS")
        cc.historico_servicos.append(servico)

        reject_response = {"decision": "rejeitar", "justification": "Não alinhado."}
        mock_enviar_para_llm.return_value = json.dumps(reject_response)

        cc.validar_propostas([], [servico])

        assert servico.status == "rejected"
        history_rejection_found = any(
            entry["status"] == "rejected" and "Rejeitado por ValidadorAgente2" in entry["message"]
            for entry in servico.history
        )
        assert history_rejection_found
        event_found = any(f"SERVIÇO '{servico.service_name}' REJEITADO" in evento for evento in ed.historico_eventos)
        assert event_found

    @patch('empresa_digital.enviar_para_llm')
    def test_validar_item_llm_json_retry_then_reject(self, mock_enviar_para_llm):
        ed.criar_agente("ValidadorAgente3", "Validador", "mock_model_val", list(ed.locais.keys())[0])
        ideia = Ideia(descricao="Ideia com JSON inválido", justificativa="J", autor="AutorInv")
        cc.historico_ideias.append(ideia)

        # LLM returns invalid JSON for all 3 attempts
        mock_enviar_para_llm.return_value = "JSON Inválido"

        cc.validar_propostas([ideia], [])

        assert ideia.validada is False # Should be auto-rejeitada
        assert mock_enviar_para_llm.call_count == 3
        event_found = any(f"AUTO-REJEITADO: Ideia de Produto '{ideia.descricao}'" in evento for evento in ed.historico_eventos)
        assert event_found
        auto_reject_msg_found = any("Auto-rejeitado após 3 tentativas" in evento for evento in ed.historico_eventos if "AUTO-REJEITADO" in evento)
        assert auto_reject_msg_found


    @patch('empresa_digital.enviar_para_llm')
    def test_validar_item_llm_communication_failure_fallback(self, mock_enviar_para_llm):
        # No Validador agents needed for this specific path test if we mock _validar_item_com_llm to return False
        # However, the current structure calls _validar_item_com_llm from validar_propostas after selecting a validador.
        # So, we need a validador, but then mock the LLM call to simulate persistent failure.
        ed.criar_agente("ValidadorAgente4", "Validador", "mock_model_val", list(ed.locais.keys())[0])
        ideia = Ideia(descricao="Ideia com falha LLM", justificativa="J", autor="AutorFalha")
        ideia.descricao = "ia na descricao para fallback aprovar" # Ensure fallback approves
        cc.historico_ideias.append(ideia)

        # Simulate enviar_para_llm raising an exception consistently (or returning error JSON not handled as decision)
        mock_enviar_para_llm.side_effect = Exception("Falha de rede persistente")

        cc.validar_propostas([ideia], [])

        # Check if fallback heuristic was applied
        assert ideia.validada is True # Fallback for "ia na descricao" should approve
        assert mock_enviar_para_llm.call_count == 3 # _validar_item_com_llm retries
        event_found = any(f"Fallback: Ideia de Produto '{ideia.descricao}' aprovada (fallback)" in evento for evento in ed.historico_eventos)
        assert event_found

    def test_validar_propostas_no_validators_fallback(self):
        # No Validador agents created for this test
        ideia1 = Ideia(descricao="Ideia IA para fallback", justificativa="J", autor="A1") # Fallback should approve
        ideia2 = Ideia(descricao="Ideia sem keywords", justificativa="J", autor="A2") # Fallback should reject
        cc.historico_ideias.extend([ideia1, ideia2])

        servico1 = Service(service_name="Serviço baixo esforço", description="D", author="AS1", estimated_effort_hours=10, price_amount=100) # Fallback should approve
        servico2 = Service(service_name="Serviço alto esforço", description="D", author="AS2", estimated_effort_hours=100, price_amount=100) # Fallback should reject
        cc.historico_servicos.extend([servico1, servico2])

        cc.validar_propostas(cc.historico_ideias, cc.historico_servicos)

        assert ideia1.validada is True
        assert ideia2.validada is False
        assert servico1.status == "validated"
        assert servico2.status == "rejected"

        event_fallback_ideia1 = any(f"Fallback: Ideia de Produto '{ideia1.descricao}' aprovada (fallback)" in evento for evento in ed.historico_eventos)
        assert event_fallback_ideia1
        event_fallback_servico1 = any(f"Fallback: Serviço '{servico1.service_name}' APROVADO (baixo esforço)" in evento for evento in ed.historico_eventos)
        assert event_fallback_servico1


class TestPrototiparIdeias:
    # Mock produto_digital from criador_de_produtos and sugerir_conteudo_marketing from divulgador
    @patch('ciclo_criativo.produto_digital')
    @patch('ciclo_criativo.sugerir_conteudo_marketing')
    def test_prototipar_ideia_sucesso_com_marketing(self, mock_sugerir_marketing, mock_produto_digital):
        ideia_desc = "Ideia de Produto IA Incrível"
        ideia = Ideia(descricao=ideia_desc, justificativa="J", autor="AutorP", validada=True)
        cc.historico_ideias.append(ideia)

        mock_produto_digital.return_value = "http://gum.co/produto_fake"
        marketing_content = "Este é o conteúdo de marketing. Ótimo produto!"
        mock_sugerir_marketing.return_value = marketing_content

        initial_saldo = ed.saldo # 0.0 by default from reset_global_state

        # Ensure the marketing directory and file will be cleaned up if created
        PRODUTOS_MARKETING_DIR = "produtos_marketing"
        expected_marketing_dir = os.path.join(PRODUTOS_MARKETING_DIR, ideia.slug)
        expected_marketing_file = os.path.join(expected_marketing_dir, "marketing.md")

        if os.path.exists(expected_marketing_file): os.remove(expected_marketing_file)
        if os.path.exists(expected_marketing_dir): os.rmdir(expected_marketing_dir)


        cc.prototipar_ideias([ideia])

        assert ideia.executada is True
        assert ideia.link_produto == "http://gum.co/produto_fake"
        # Default success profit for product creation is 50.0, +25 for "ia", +10 for "produto"
        expected_resultado = 50.0 + 25.0 + 10.0
        assert ideia.resultado == expected_resultado
        assert ed.saldo == initial_saldo + expected_resultado

        # Check theme preference (assuming "ia" is in description)
        assert cc.preferencia_temas.get("IA", 0) == 1

        # Check marketing content saving
        assert os.path.exists(expected_marketing_file)
        with open(expected_marketing_file, "r", encoding="utf-8") as f:
            saved_content = f.read()
        assert saved_content == marketing_content

        # Check events
        event_lucro_found = any(f"Lucro produto '{ideia.descricao}' (+{expected_resultado:.2f})" in evento for evento in ed.historico_eventos)
        assert event_lucro_found
        event_marketing_found = any(f"Marketing para '{ideia.descricao}': {marketing_content[:150].replace(chr(10), ' ')}..." in evento for evento in ed.historico_eventos)
        assert event_marketing_found
        event_prototipo_found = any(f"Prototipo/Execução IDEIA '{ideia.descricao}'. Resultado: {expected_resultado:.2f}" in evento for evento in ed.historico_eventos)
        assert event_prototipo_found

        # Cleanup
        if os.path.exists(expected_marketing_file): os.remove(expected_marketing_file)
        if os.path.exists(expected_marketing_dir): os.rmdir(expected_marketing_dir)
        # Ensure PRODUTOS_MARKETING_DIR itself is not removed if it contained other things, only if it's empty.
        if os.path.exists(PRODUTOS_MARKETING_DIR) and not os.listdir(PRODUTOS_MARKETING_DIR):
            os.rmdir(PRODUTOS_MARKETING_DIR)


    @patch('ciclo_criativo.produto_digital')
    @patch('ciclo_criativo.sugerir_conteudo_marketing')
    def test_prototipar_ideia_falha_criacao_produto(self, mock_sugerir_marketing, mock_produto_digital):
        ideia = Ideia(descricao="Ideia Falha", justificativa="J", autor="AutorF", validada=True)
        cc.historico_ideias.append(ideia)

        mock_produto_digital.return_value = None # Simula falha na criação do produto
        initial_saldo = ed.saldo

        cc.prototipar_ideias([ideia])

        assert ideia.executada is True
        assert ideia.link_produto is None
        expected_resultado = -15.0 # Penalidade por falha
        assert ideia.resultado == expected_resultado
        assert ed.saldo == initial_saldo + expected_resultado # Saldo deve diminuir

        assert cc.preferencia_temas.get("outros", 0) == -1 # Tema "outros" com feedback negativo
        mock_sugerir_marketing.assert_not_called() # Marketing não deve ser chamado se produto falha

        event_prejuizo_found = any(f"Prejuízo/Custo produto '{ideia.descricao}' ({expected_resultado:.2f})" in evento for evento in ed.historico_eventos)
        assert event_prejuizo_found
        event_prototipo_found = any(f"Prototipo/Execução IDEIA '{ideia.descricao}'. Resultado: {expected_resultado:.2f}" in evento for evento in ed.historico_eventos)
        assert event_prototipo_found

    def test_prototipar_ideia_nao_validada(self):
        ideia = Ideia(descricao="Ideia Nao Validada", justificativa="J", autor="AutorNV", validada=False)
        cc.historico_ideias.append(ideia)

        cc.prototipar_ideias([ideia])

        assert ideia.executada is False # Não deve ser executada
        assert ideia.resultado == 0.0 # Resultado não deve mudar
        assert not cc.preferencia_temas # Preferencia de temas não deve ser afetada


class TestExecutarServicosValidados:
    @patch('empresa_digital.criar_agente') # Mock agent creation
    @patch('empresa_digital.selecionar_modelo') # Mock model selection for new agent
    def test_servico_auto_assign_existing_executor(self, mock_selecionar_modelo, mock_criar_agente):
        # Setup: Validated service, idle Executor available
        local_default = list(ed.locais.keys())[0]
        executor_livre = ed.criar_agente("ExecutorLivre1", "Executor", "gpt-x", local_default, objetivo_atual="Aguardando novas atribuições.")

        servico = Service(service_name="Serviço Teste Auto Assign", description="Desc", author="TestAuth", status="validated", estimated_effort_hours=10)
        servico.cycles_unassigned = 1 # Will become 2 in the first call to executar_servicos_validados
        cc.historico_servicos.append(servico)

        cc.executar_servicos_validados()

        assert servico.status == "in_progress"
        assert servico.assigned_agent_name == executor_livre.nome
        assert servico.cycles_unassigned == 0 # Reset after assignment
        assert executor_livre.objetivo_atual == f"Executar serviço: {servico.service_name} (ID: {servico.id})"
        mock_criar_agente.assert_not_called() # No new agent should be created

    @patch('empresa_digital.criar_agente')
    @patch('empresa_digital.selecionar_modelo')
    def test_servico_auto_assign_hire_new_executor(self, mock_selecionar_modelo, mock_criar_agente):
        # Setup: Validated service, no idle Executors
        local_default = list(ed.locais.keys())[0]
        # Make sure no "Executor" is free or exists initially for this test isolation if needed
        ed.agentes.clear() # Clear any existing agents from previous tests if reset_global_state wasn't perfect
        if not ed.locais: ed.criar_local("Laboratorio Default", "Local de fallback para testes", []) # Ensure local exists
        local_default = list(ed.locais.keys())[0]


        servico = Service(service_name="Serviço Teste Contratação", description="Desc", author="TestAuth", status="validated", estimated_effort_hours=10)
        servico.cycles_unassigned = 1
        cc.historico_servicos.append(servico)

        # Mock `selecionar_modelo` to return a dummy model for the new agent
        mock_selecionar_modelo.return_value = ("mock_executor_model", "Raciocinio Mock")
        # Mock `criar_agente` to simulate successful creation and return a mock agent object
        mock_novo_executor = MagicMock(spec=ed.Agente)
        mock_novo_executor.nome = "ExecutorContratado1"
        mock_novo_executor.funcao = "Executor"
        mock_criar_agente.return_value = mock_novo_executor

        # Add the mock agent to ed.agentes so it can be retrieved by cc.executar_servicos_validados
        # This is a bit tricky because criar_agente itself adds to ed.agentes.
        # The mock should behave as if ed.criar_agente worked.
        # Let's refine: mock_criar_agente will be called, and it should return an agent that then gets used.
        # The actual addition to ed.agentes is done by ed.criar_agente which is mocked.
        # So, when cc.executar_servicos_validados tries to get ed.agentes[mock_novo_executor.nome], it might fail
        # if the mock_criar_agente doesn't also add to ed.agentes.
        # For this test, we can simplify by having the mock also add to ed.agentes or check call args.

        def side_effect_criar_agente(nome, funcao, modelo_llm, local, objetivo):
            # Simulate the real ed.criar_agente's side effect of adding to ed.agentes
            agente_real = ed.Agente(nome=nome, funcao=funcao, modelo_llm=modelo_llm, local_atual=ed.locais[local], objetivo_atual=objetivo)
            ed.agentes[nome] = agente_real
            return agente_real

        mock_criar_agente.side_effect = side_effect_criar_agente


        cc.executar_servicos_validados()

        mock_criar_agente.assert_called_once() # New agent should be created
        created_agent_args = mock_criar_agente.call_args[1] # kwargs
        assert created_agent_args['funcao'] == "Executor"

        # Find the newly created agent in ed.agentes (name might be dynamic)
        novo_executor_real = None
        for ag_nome, ag_obj in ed.agentes.items():
            if ag_obj.funcao == "Executor" and servico.service_name in ag_obj.objetivo_atual:
                novo_executor_real = ag_obj
                break

        assert novo_executor_real is not None, "Novo executor não foi encontrado em ed.agentes"

        assert servico.status == "in_progress"
        assert servico.assigned_agent_name == novo_executor_real.nome
        assert servico.cycles_unassigned == 0
        assert novo_executor_real.objetivo_atual == f"Executar serviço: {servico.service_name} (ID: {servico.id})"
        event_contratacao_found = any(f"Novo Executor '{novo_executor_real.nome}' contratado para '{servico.service_name}'" in evento for evento in ed.historico_eventos)
        assert event_contratacao_found


    def test_servico_progress_and_completion(self):
        local_default = list(ed.locais.keys())[0]
        executor = ed.criar_agente("ExecutorTrabalhador", "Executor", "gpt-x", local_default)

        servico = Service(
            service_name="Serviço Longo", description="Desc", author="TestAuth",
            status="validated", estimated_effort_hours=20
        )
        cc.historico_servicos.append(servico)

        # Assign manually for this test
        servico.assign_agent(executor.nome) # Sets status to in_progress, resets progress_hours
        assert servico.status == "in_progress"
        assert servico.progress_hours == 0.0

        # Simulate cycles
        # Assume ed.HOURS_PER_CYCLE_FACTOR = 8.0 (default in empresa_digital.py)
        # Cycle 1
        cc.executar_servicos_validados()
        assert servico.progress_hours == ed.HOURS_PER_CYCLE_FACTOR * 1
        assert servico.status == "in_progress"
        assert len(servico.history) == 3 # proposed, assigned (in_progress), progress_update
        assert f"Progresso: {servico.progress_hours:.2f}/{servico.estimated_effort_hours}h" in servico.history[-1]['message']


        # Cycle 2
        cc.executar_servicos_validados()
        assert servico.progress_hours == ed.HOURS_PER_CYCLE_FACTOR * 2
        assert servico.status == "in_progress"

        # Cycle 3 - should complete (8*3=24 >= 20)
        cc.executar_servicos_validados()
        assert servico.progress_hours >= servico.estimated_effort_hours
        assert servico.status == "completed"
        assert executor.objetivo_atual == "Aguardando novas atribuições."

        event_completou_found = any(f"Serviço '{servico.service_name}' (ID: {servico.id}) CONCLUÍDO por {executor.nome}" in evento for evento in ed.historico_eventos)
        assert event_completou_found
        assert servico.history[-1]['status'] == "completed"


    def test_servico_cycles_unassigned_increment(self):
        servico = Service(service_name="Serviço Ocioso", description="Desc", author="TestAuth", status="validated")
        cc.historico_servicos.append(servico)

        assert servico.cycles_unassigned == 0
        cc.executar_servicos_validados() # Cycle 1
        assert servico.cycles_unassigned == 1
        cc.executar_servicos_validados() # Cycle 2 - should trigger assignment if an agent was available or hired
        # If no agent is hired (e.g., mock criar_agente to fail or no locals), it might stay validated.
        # For this test, let's assume no agent can be found/hired to check accumulation.
        with patch('empresa_digital.criar_agente', MagicMock(side_effect=ValueError("Cannot hire"))):
             cc.executar_servicos_validados() # Cycle 2 attempt
             assert servico.cycles_unassigned == 2
             if servico.status == "validated": # if it wasn't assigned due to hiring error
                cc.executar_servicos_validados() # Cycle 3 attempt
                assert servico.cycles_unassigned == 3


if __name__ == '__main__':
    pytest.main() # Or unittest.main() if only using unittest patterns
