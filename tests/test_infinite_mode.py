import empresa_digital as ed
from ciclo_criativo import executar_ciclo_criativo
import rh


def test_infinite_mode_generates_events(reset_state):
    ed.definir_modo_vida_infinita(True)
    ed.criar_local("Lab", "", ["pc"])
    ed.criar_agente("Alice", "Ideacao", "gpt", "Lab")
    ed.criar_agente("Bob", "Validador", "gpt", "Lab")
    ed.adicionar_tarefa("T1")
    ed.saldo = 100
    rh.modulo_rh.verificar()

    for _ in range(3):
        ed.historico_eventos.clear()
        executar_ciclo_criativo()
        for ag in list(ed.agentes.values()):
            prompt = ed.gerar_prompt_decisao(ag)
            resp = ed.enviar_para_llm(ag, prompt)
            ed.executar_resposta(ag, resp)
        ed.calcular_lucro_ciclo()
        assert ed.historico_eventos, "Sem eventos no ciclo"

