"""Automatic hiring module for the digital company.

Provides the :class:`ModuloRH` used to create and allocate new agents when
there is available balance and unmet demand or pending tasks.
"""

import logging
import random
from typing import Dict

import empresa_digital as ed
from empresa_digital import (
    MODO_VIDA_INFINITA,
    agentes,
    locais,
    criar_agente,
    tarefas_pendentes,
    selecionar_modelo,
    registrar_evento,
)

logger = logging.getLogger(__name__)


class ModuloRH:
    """Modulo de RH responsavel por criar agentes automaticamente."""

    def __init__(self, min_por_sala: int = 1, min_por_funcao: int = 1, modelo_padrao: str = "gpt-3.5-turbo") -> None:
        self.min_por_sala = min_por_sala
        self.min_por_funcao = min_por_funcao
        self.modelo_padrao = modelo_padrao
        self._contador = 1

    def _novo_nome(self) -> str:
        nome = f"Auto{self._contador}"
        self._contador += 1
        return nome

    def verificar(self) -> None:
        """Verifica carencias e contrata new agentes se necessario."""
        # Usa o saldo atual do modulo principal para decidir sobre contratações
        if not MODO_VIDA_INFINITA: # Only apply saldo logic if not in infinite mode
            if ed.saldo <= 0:
                logger.info("Saldo insuficiente para contratações regulares.")
                registrar_evento("RH: saldo atual insuficiente para contratações regulares.")
                if ed.tarefas_pendentes and len(ed.agentes) < 2 and random.random() < 0.1: # 10% chance
                    ed.saldo += 20.0 # Emergency fund
                    registrar_evento("RH: Fundo de emergência (20.0) ativado para garantir operações mínimas devido a tarefas pendentes e poucos agentes.")
                    logger.info("RH: Fundo de emergência de 20.0 ativado. Saldo atual: %s", ed.saldo)

                if ed.saldo <= 0:
                    logger.info("Saldo ainda insuficiente após verificação de emergência, nenhuma contratação realizada.")
                    registrar_evento("RH: saldo ainda insuficiente após verificação de emergência.")
                    return
        else: # In MODO_VIDA_INFINITA
            registrar_evento("RH: MODO VIDA INFINITA ATIVO - Restrições de saldo ignoradas para contratação.")
            logger.info("RH: MODO VIDA INFINITA ATIVO - Restrições de saldo ignoradas para contratação.")
            # Optionally ensure saldo is very high for any logic downstream that might still check it.
            if ed.saldo < 1000: # Ensure a high baseline for any other checks
                ed.saldo = 10000.0
                registrar_evento("RH: MODO VIDA INFINITA - Saldo artificialmente elevado para 10000.")

        contratou = False

        # Verifica cada sala com carencia de agentes
        for local in sorted(locais.values(), key=lambda l: l.nome):
            if len(local.agentes_presentes) < self.min_por_sala and tarefas_pendentes:
                nome = self._novo_nome()
                modelo, motivo = selecionar_modelo("Funcionario")
                criar_agente(nome, "Funcionario", modelo, local.nome)
                msg = f"RH contratou {nome} para {local.nome} - {motivo}"
                logger.info(
                    "Novo agente %s alocado em %s por falta de pessoal - %s",
                    nome,
                    local.nome,
                    motivo,
                )
                registrar_evento(msg)
                contratou = True

        # Conta agentes por funcao
        contagem_funcao: Dict[str, int] = {}
        for ag in agentes.values():
            contagem_funcao[ag.funcao] = contagem_funcao.get(ag.funcao, 0) + 1
        for funcao, qtd in contagem_funcao.items():
            if qtd < self.min_por_funcao and tarefas_pendentes:
                nome = self._novo_nome()
                primeiro_local = min(locais.values(), key=lambda l: l.nome, default=None)
                if primeiro_local:
                    modelo, motivo = selecionar_modelo(funcao)
                    criar_agente(nome, funcao, modelo, primeiro_local.nome)
                    msg = (
                        f"RH contratou {nome} para funcao {funcao} - {motivo}"
                    )
                    logger.info(
                        "Novo agente %s contratado para funcao %s (apenas %d existentes) - %s",
                        nome,
                        funcao,
                        qtd,
                        motivo,
                    )
                    registrar_evento(msg)
                    contratou = True

        # Cria agentes para tarefas pendentes
        while tarefas_pendentes:
            tarefa = tarefas_pendentes.pop(0)
            primeiro_local = min(locais.values(), key=lambda l: l.nome, default=None)
            if primeiro_local:
                nome = self._novo_nome()
                modelo, motivo = selecionar_modelo("Executor", tarefa)
                criar_agente(
                    nome,
                    "Executor",
                    modelo,
                    primeiro_local.nome,
                    objetivo=tarefa,
                )
                msg = f"RH criou {nome} para tarefa '{tarefa}' - {motivo}"
                logger.info(
                    "Agente %s criado para tarefa pendente '%s' - %s",
                    nome,
                    tarefa,
                    motivo,
                )
                registrar_evento(msg)
                contratou = True

        if not contratou:
            logger.info("Nenhuma contratacao necessaria neste ciclo")
            registrar_evento("RH: nenhuma contratacao necessaria")


modulo_rh = ModuloRH()
