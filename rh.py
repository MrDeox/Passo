import logging
from typing import Dict

from empresa_digital import (
    agentes,
    locais,
    criar_agente,
    tarefas_pendentes,
    saldo,
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

        # Verifica cada sala
        for local in locais.values():
            if len(local.agentes_presentes) < self.min_por_sala and tarefas_pendentes:
                nome = self._novo_nome()
                criar_agente(nome, "Funcionario", self.modelo_padrao, local.nome)
                logger.info("Novo agente %s alocado em %s por falta de pessoal", nome, local.nome)
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
                    criar_agente(nome, funcao, self.modelo_padrao, primeiro_local.nome)
                    logger.info(
                        "Novo agente %s contratado para funcao %s (apenas %d existentes)",
                        nome,
                        funcao,
                        qtd,
                    )
                    contratou = True

        # Cria agentes para tarefas pendentes
        while tarefas_pendentes:
            tarefa = tarefas_pendentes.pop(0)
            primeiro_local = next(iter(locais.values()), None)
            if primeiro_local:
                nome = self._novo_nome()
                criar_agente(
                    nome,
                    "Executor",
                    self.modelo_padrao,
                    primeiro_local.nome,
                    objetivo=tarefa,
                )
                logger.info("Agente %s criado para tarefa pendente '%s'", nome, tarefa)
                contratou = True

        if not contratou:
            logger.info("Nenhuma contratacao necessaria neste ciclo")


modulo_rh = ModuloRH()
