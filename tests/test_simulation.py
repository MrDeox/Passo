import empresa_digital as ed
import rh
from ciclo_criativo import executar_ciclo_criativo


def test_simulation_cycle_updates_state(reset_state):
    """Executa um ciclo manualmente e verifica atualizações de saldo e eventos."""
    ed.criar_local("Lab", "desc", ["pc"])
    ed.criar_agente("Alice", "Ideacao", "gpt", "Lab")
    ed.criar_agente("Bob", "Validador", "gpt", "Lab")
    ed.adicionar_tarefa("T1")
    ed.saldo = 20
    rh.saldo = ed.saldo
    rh.modulo_rh.verificar()

    executar_ciclo_criativo()
    for ag in list(ed.agentes.values()):
        prompt = ed.gerar_prompt_decisao(ag)
        resp = ed.enviar_para_llm(ag, prompt)
        ed.executar_resposta(ag, resp)
    result = ed.calcular_lucro_ciclo()

    assert result["saldo"] != 0
    assert ed.historico_saldo[-1] == result["saldo"]
    assert ed.historico_eventos
