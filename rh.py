"""Automatic hiring module for the digital company.

Provides the :class:`ModuloRH` used to create and allocate new agents when
there is available balance and unmet demand or pending tasks.
"""

import logging
from typing import Dict

from empresa_digital import (
    agentes,
    locais,
    criar_agente,
    tarefas_pendentes,
    saldo,
    selecionar_modelo,
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
        """Verifica carencias e contrata novos agentes se necessario."""
        if saldo <= 0:
            logger.info("Saldo insuficiente, nenhuma contratacao realizada")
            return

        contratou = False

        # Verifica cada sala com carencia de agentes
        for local in locais.values():
            if len(local.agentes_presentes) < self.min_por_sala and tarefas_pendentes:
                nome = self._novo_nome()
                modelo, motivo = selecionar_modelo("Funcionario")
                criar_agente(nome, "Funcionario", modelo, local.nome)
                logger.info(
                    "Novo agente %s alocado em %s por falta de pessoal - %s",
                    nome,
                    local.nome,
                    motivo,
                )
                contratou = True

        # Conta agentes por funcao
        contagem_funcao: Dict[str, int] = {}
        for ag in agentes.values():
            contagem_funcao[ag.funcao] = contagem_funcao.get(ag.funcao, 0) + 1
        for funcao, qtd in contagem_funcao.items():
            if qtd < self.min_por_funcao and tarefas_pendentes:
                nome = self._novo_nome()
                primeiro_local = next(iter(locais.values()), None)
                if primeiro_local:
                    modelo, motivo = selecionar_modelo(funcao)
                    criar_agente(nome, funcao, modelo, primeiro_local.nome)
                    logger.info(
                        "Novo agente %s contratado para funcao %s (apenas %d existentes) - %s",
                        nome,
                        funcao,
                        qtd,
                        motivo,
                    )
                    contratou = True

        # Cria agentes para tarefas pendentes
        while tarefas_pendentes:
            tarefa = tarefas_pendentes.pop(0)
            primeiro_local = next(iter(locais.values()), None)
            if primeiro_local:
                nome = self._novo_nome()
                modelo, motivo = selecionar_modelo("Executor")
                criar_agente(
                    nome,
                    "Executor",
                    modelo,
                    primeiro_local.nome,
                    objetivo=tarefa,
                )
                logger.info(
                    "Agente %s criado para tarefa pendente '%s' - %s",
                    nome,
                    tarefa,
                    motivo,
                )
                contratou = True

        if not contratou:
            logger.info("Nenhuma contratacao necessaria neste ciclo")


modulo_rh = ModuloRH()
