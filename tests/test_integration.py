"""Testes de integração simulando um ciclo completo."""

import empresa_digital as ed
import rh
from ciclo_criativo import executar_ciclo_criativo


def test_ciclo_completo_altera_saldo():
    # Configura dois locais e agentes basicos
    ed.criar_local("Tecnologia", "", ["pc"])
    ed.criar_local("Reuniao", "", [])
    ed.criar_agente("Alice", "Ideacao", "gpt", "Tecnologia")
    ed.criar_agente("Bob", "Validador", "gpt", "Reuniao")

    # Tarefa inicial para acionar o RH
    ed.adicionar_tarefa("Inicial")
    ed.saldo = 20
    rh.saldo = ed.saldo
    rh.modulo_rh.verificar()

    # Ciclo criativo gera nova tarefa
    executar_ciclo_criativo()

    # Executa decisoes simuladas para cada agente
    for ag in list(ed.agentes.values()):
        prompt = ed.gerar_prompt_decisao(ag)
        resp = ed.enviar_para_llm(ag, prompt)
        ed.executar_resposta(ag, resp)

    result = ed.calcular_lucro_ciclo()

    # Verifica contratacao e atualizacao do saldo
    assert "Auto1" in ed.agentes
    assert result["saldo"] == 13.0
    assert ed.historico_saldo[-1] == 13.0
    assert ed.tarefas_pendentes  # tarefa gerada pelo ciclo criativo

