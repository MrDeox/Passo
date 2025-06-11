import empresa_digital # For functions
import state # Added
import config # Added
from ciclo_criativo import executar_ciclo_criativo
import rh


def test_infinite_mode_generates_events(reset_state):
    empresa_digital.definir_modo_vida_infinita(True) # This sets state.MODO_VIDA_INFINITA
    empresa_digital.criar_local("Lab", "", ["pc"])
    empresa_digital.criar_agente("Alice", "Ideacao", "gpt", "Lab")
    empresa_digital.criar_agente("Bob", "Validador", "gpt", "Lab")
    empresa_digital.adicionar_tarefa("T1")
    state.saldo = 100
    rh.modulo_rh.verificar() # rh.py should use state internally

    for _ in range(3):
        state.historico_eventos.clear()
        executar_ciclo_criativo() # ciclo_criativo.py should use state internally
        for ag in list(state.agentes.values()):
            prompt = empresa_digital.gerar_prompt_decisao(ag)
            resp = empresa_digital.enviar_para_llm(ag, prompt)
            empresa_digital.executar_resposta(ag, resp)
        empresa_digital.calcular_lucro_ciclo()
        assert state.historico_eventos, "Sem eventos no ciclo"

