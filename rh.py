"""Automatic hiring module for the digital company.

Provides the :class:`ModuloRH` used to create and allocate new agents when
there is available balance and unmet demand or pending tasks.
"""

import logging
import random # Ensure random is imported
from typing import Dict, List # List for iterating over a copy

import empresa_digital as ed
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
        if not ed.MODO_VIDA_INFINITA:  # Only apply saldo logic if not in infinite mode
            if ed.saldo <= 0:
                logger.info("Saldo insuficiente para contratações regulares.")
                ed.registrar_evento("RH: saldo atual insuficiente para contratações regulares.")
                if ed.tarefas_pendentes and len(ed.agentes) < 2 and random.random() < 0.1:  # 10% chance
                    ed.saldo += 20.0 # Emergency fund
                    ed.registrar_evento(
                        "RH: Fundo de emergência (20.0) ativado para garantir operações mínimas devido a tarefas pendentes e poucos agentes."
                    )
                    logger.info("RH: Fundo de emergência de 20.0 ativado. Saldo atual: %s", ed.saldo)

                if ed.saldo <= 0:
                    logger.info("Saldo ainda insuficiente após verificação de emergência, nenhuma contratação realizada.")
                    ed.registrar_evento("RH: saldo ainda insuficiente após verificação de emergência.")
                    return
        else:  # In MODO_VIDA_INFINITA
            ed.registrar_evento(
                "RH: MODO VIDA INFINITA ATIVO - Restrições de saldo ignoradas para contratação."
            )
            logger.info("RH: MODO VIDA INFINITA ATIVO - Restrições de saldo ignoradas para contratação.")
            # Optionally ensure saldo is very high for any logic downstream that might still check it.
            if ed.saldo < 1000: # Ensure a high baseline for any other checks
                ed.saldo = 10000.0
                ed.registrar_evento("RH: MODO VIDA INFINITA - Saldo artificialmente elevado para 10000.")

        contratou = False

        # Verifica cada sala com carencia de agentes
        for local in sorted(ed.locais.values(), key=lambda l: l.nome):
            if len(local.agentes_presentes) < self.min_por_sala and ed.tarefas_pendentes:
                nome = self._novo_nome()
                modelo, motivo = ed.selecionar_modelo("Funcionario")
                ed.criar_agente(nome, "Funcionario", modelo, local.nome)
                msg = f"RH contratou {nome} para {local.nome} - {motivo}"
                logger.info(
                    "Novo agente %s alocado em %s por falta de pessoal - %s",
                    nome,
                    local.nome,
                    motivo,
                )
                ed.registrar_evento(msg)
                contratou = True

        # Conta agentes por funcao
        contagem_funcao: Dict[str, int] = {}
        for ag in ed.agentes.values():
            contagem_funcao[ag.funcao] = contagem_funcao.get(ag.funcao, 0) + 1
        for funcao, qtd in contagem_funcao.items():
            if qtd < self.min_por_funcao and ed.tarefas_pendentes:
                nome = self._novo_nome()
                primeiro_local = min(ed.locais.values(), key=lambda l: l.nome, default=None)
                if primeiro_local:
                    modelo, motivo = ed.selecionar_modelo(funcao)
                    ed.criar_agente(nome, funcao, modelo, primeiro_local.nome)
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
                    ed.registrar_evento(msg)
                    contratou = True

        # Cria agentes para tarefas pendentes (agora `ed.tarefas_pendentes` contém objetos Task)
        while ed.tarefas_pendentes:
            tarefa_obj = ed.tarefas_pendentes.pop(0) # Pop um objeto Task

            # Processar apenas tarefas que estão "todo" para criação de novos agentes.
            # Tarefas "in_progress" ou "done" não deveriam estar aqui para contratação.
            # Se uma tarefa "in_progress" está aqui, significa que o agente anterior pode ter sido removido.
            # Por ora, vamos focar em criar agentes para tarefas "todo".
            # Se uma tarefa já está "in_progress", não deveríamos criar um novo agente para ela aqui,
            # a menos que a lógica de reatribuição seja explicitamente desejada no RH.
            # Para o escopo atual, apenas tarefas "todo" devem gerar novos agentes.
            if tarefa_obj.status != "todo":
                logger.warning(f"RH encontrou tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) com status '{tarefa_obj.status}' na fila de pendências. Esperado 'todo'. Tarefa será devolvida à fila.")
                ed.tarefas_pendentes.insert(0, tarefa_obj) # Devolve ao início da fila para evitar loop infinito se for sempre a primeira
                # Ou considerar uma lista separada para tarefas problemáticas.
                # Para evitar loops, se a primeira tarefa não for 'todo', podemos parar de processar neste ciclo.
                if ed.tarefas_pendentes[0].status != "todo": # Se a primeira ainda não é 'todo'
                    break # Evita processar a mesma tarefa não 'todo' repetidamente.
                continue


            primeiro_local_obj = min(ed.locais.values(), key=lambda l: l.nome, default=None)
            if not primeiro_local_obj:
                logger.error("Não há locais definidos. Impossível criar novo Executor para a tarefa. Devolvendo tarefa à fila.")
                ed.tarefas_pendentes.insert(0, tarefa_obj) # Devolve a tarefa ao início da fila
                break # Interrompe o loop de criação de agentes para tarefas se não há locais

            novo_executor_nome = self._novo_nome()
            modelo_llm_executor, motivo_modelo = ed.selecionar_modelo("Executor", f"Executar tarefa: {tarefa_obj.description}")

            try:
                # Atualizar status da tarefa para "in_progress" ANTES de criar o agente
                # A mensagem de log aqui é importante para rastrear quem foi designado.
                tarefa_obj.update_status("in_progress", f"Atribuída ao novo agente {novo_executor_nome} a ser criado.")
                logger.info(f"Tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) status atualizado para 'in_progress'.")
                ed.registrar_evento(f"Tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) status: in_progress, sendo atribuída a {novo_executor_nome}.")

                novo_executor = ed.criar_agente(
                    nome=novo_executor_nome,
                    funcao="Executor",
                    modelo_llm=modelo_llm_executor,
                    local=primeiro_local_obj.nome, # Nome do local
                    objetivo=f"task_id:{tarefa_obj.id}" # Definir objetivo com o ID da tarefa
                )
                # Log após criação bem sucedida do agente
                msg = f"RH criou Executor '{novo_executor.nome}' para tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}). Motivo LLM: {motivo_modelo}"
                logger.info(msg)
                ed.registrar_evento(msg)
                contratou = True
            except ValueError as e: # Erro ao criar agente
                logger.error(f"Falha ao criar novo Executor '{novo_executor_nome}' para a tarefa '{tarefa_obj.description}': {e}")
                # Reverter status da tarefa para "todo"
                tarefa_obj.update_status("todo", f"Criação do agente {novo_executor_nome} falhou. Retornando para 'todo'.")
                logger.warning(f"Status da tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) revertido para 'todo' devido à falha na criação do agente.")
                ed.registrar_evento(f"Falha ao criar agente para tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}). Status revertido para 'todo'.")
                ed.tarefas_pendentes.insert(0, tarefa_obj) # Devolve a tarefa ao início da fila
            except Exception as e_geral: # Outros erros inesperados
                logger.error(f"Erro inesperado ao tentar criar agente para tarefa '{tarefa_obj.description}': {e_geral}", exc_info=True)
                # Tentar reverter status se possível, ou logar inconsistência
                if tarefa_obj.status == "in_progress": # Se o status foi mudado
                    tarefa_obj.update_status("todo", f"Erro crítico na criação do agente {novo_executor_nome}. Retornando para 'todo'.")
                    logger.warning(f"Status da tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) revertido para 'todo' devido a erro crítico.")
                ed.tarefas_pendentes.insert(0, tarefa_obj) # Devolve a tarefa

        if not contratou:
            logger.info("Nenhuma contratacao necessaria neste ciclo")
            ed.registrar_evento("RH: nenhuma contratacao necessaria")

        # --- Logic for Incrementing Idle Cycles and Optional Layoff/Role Change for Executors ---
        logger.info("RH: Verificando ociosidade de Executores...")
        agentes_para_remover: List[ed.Agente] = [] # Store agents to be dismissed

        # First, increment idle cycles or reset them
        for agente in ed.agentes.values():
            if agente.funcao.lower() == "executor":
                # Define what constitutes an "idle" objective
                is_idle = not agente.objetivo_atual or \
                            agente.objetivo_atual.strip() == "" or \
                            "aguardando" in agente.objetivo_atual.lower() or \
                            agente.objetivo_atual == "Nenhum" # Consistent with some default messages

                if is_idle:
                    agente.cycles_idle += 1
                    logger.debug(f"Executor {agente.nome} está ocioso. Ciclos ocioso: {agente.cycles_idle}.")
                else:
                    if agente.cycles_idle > 0: # Log only if it's a change from idle
                        logger.info(f"Executor {agente.nome} não está mais ocioso (objetivo: {agente.objetivo_atual}). Zerando contador de ociosidade.")
                    agente.cycles_idle = 0  # Reset if they have work

        # Now, decide on layoffs or role changes for those with enough idle cycles
        # Iterate over a copy of values for safe removal from ed.agentes if needed
        for agente in list(ed.agentes.values()):
            if agente.funcao.lower() == "executor" and agente.cycles_idle >= 5:
                if random.random() < 0.5:  # 50% chance to dismiss
                    agentes_para_remover.append(agente)
                    logger.info(f"RH: Executor ocioso {agente.nome} selecionado para dispensa após {agente.cycles_idle} ciclos.")
                    ed.registrar_evento(f"RH: Executor {agente.nome} selecionado para dispensa por ociosidade ({agente.cycles_idle} ciclos).")
                else: # Other 50% chance to redefine role
                    old_funcao = agente.funcao
                    agente.funcao = "Funcionario" # Generic role
                    agente.objetivo_atual = "Aguardando novas diretrizes como Funcionario."
                    agente.cycles_idle = 0  # Reset idle counter
                    logger.info(f"RH: Executor ocioso {agente.nome} teve função redefinida para 'Funcionario' após {agente.cycles_idle} ciclos.")
                    ed.registrar_evento(f"RH: Executor {agente.nome} redefinido para 'Funcionario' por ociosidade ({agente.cycles_idle} ciclos). Antiga função: {old_funcao}.")

        # Perform removals
        if agentes_para_remover:
            logger.info(f"RH: Processando dispensa de {len(agentes_para_remover)} Executores ociosos.")
        for agente_a_remover in agentes_para_remover:
            if agente_a_remover.local_atual:
                agente_a_remover.local_atual.remover_agente(agente_a_remover)
                logger.debug(f"Executor {agente_a_remover.nome} removido do local {agente_a_remover.local_atual.nome}.")

            if agente_a_remover.nome in ed.agentes:
                del ed.agentes[agente_a_remover.nome]
                logger.info(f"Executor {agente_a_remover.nome} efetivamente dispensado e removido do sistema.")
                ed.registrar_evento(f"DISPENSA: Executor {agente_a_remover.nome} removido do sistema por ociosidade.")
            else:
                logger.warning(f"RH: Tentativa de dispensar {agente_a_remover.nome}, mas não encontrado em ed.agentes (pode já ter sido removido).")


modulo_rh = ModuloRH()
