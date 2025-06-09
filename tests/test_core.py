"""Testes unitários das funções principais."""

import empresa_digital as ed
import rh
from ciclo_criativo import executar_ciclo_criativo, historico_ideias


def test_criar_agente():
    local = ed.criar_local("Sala A", "Teste", [])
    ag = ed.criar_agente("Zed", "Dev", "gpt", "Sala A")
    assert ag in local.agentes_presentes
    assert ed.agentes["Zed"] is ag
    assert ag.local_atual is local


def test_mover_agente():
    l1 = ed.criar_local("A", "", [])
    l2 = ed.criar_local("B", "", [])
    ag = ed.criar_agente("X", "Func", "gpt", "A")
    ed.mover_agente("X", "B")
    assert ag.local_atual is l2
    assert ag not in l1.agentes_presentes
    assert ag in l2.agentes_presentes


def test_calcular_lucro_ciclo():
    l1 = ed.criar_local("A", "", ["pc", "mesa"])
    l2 = ed.criar_local("B", "", ["notebook"])
    a1 = ed.criar_agente("A1", "Func", "gpt", "A")
    a2 = ed.criar_agente("A2", "Func", "gpt", "B")
    a1.historico_acoes.append("acao ok")
    a2.historico_acoes.append("falha")
    res = ed.calcular_lucro_ciclo()
    assert res["receita"] == 10.0
    assert res["custos"] == 13.0
    assert res["saldo"] == -3.0
    assert ed.historico_saldo[-1] == -3.0


def test_rh_verificar_cria_agentes():
    ed.criar_local("Lab", "", [])
    ed.adicionar_tarefa("Coisa")
    ed.saldo = 10
    rh.saldo = ed.saldo
    rh.modulo_rh.verificar()
    assert "Auto1" in ed.agentes
    assert ed.tarefas_pendentes == []


def test_ciclo_criativo_gera_tarefa():
    ed.criar_local("Sala", "", [])
    ed.criar_agente("ID", "Ideacao", "gpt", "Sala")
    ed.criar_agente("VAL", "Validador", "gpt", "Sala")
    executar_ciclo_criativo()
    assert len(historico_ideias) == 1
    assert ed.tarefas_pendentes

