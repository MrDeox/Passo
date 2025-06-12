import empresa_digital # For functions
import state # Added
import rh
from ciclo_criativo import executar_ciclo_criativo


def test_simulation_cycle_updates_state(reset_state):
    """Executa um ciclo manualmente e verifica atualizações de saldo e eventos."""
    empresa_digital.criar_local("Lab", "desc", ["pc"])
    empresa_digital.criar_agente("Alice", "Ideacao", "gpt", "Lab")
    empresa_digital.criar_agente("Bob", "Validador", "gpt", "Lab")
    empresa_digital.adicionar_tarefa("T1")
    state.saldo = 20
    # rh.saldo = state.saldo # rh.py should use state.saldo directly
    rh.modulo_rh.verificar() # rh.py uses state

    executar_ciclo_criativo() # ciclo_criativo.py uses state
    for ag in list(state.agentes.values()):
        prompt = empresa_digital.gerar_prompt_decisao(ag)
        resp = empresa_digital.enviar_para_llm(ag, prompt)
        empresa_digital.executar_resposta(ag, resp)
    result = empresa_digital.calcular_lucro_ciclo()

    assert result["saldo"] != 0
    assert state.historico_saldo[-1] == result["saldo"] # Check state
    assert state.historico_eventos # Check state
