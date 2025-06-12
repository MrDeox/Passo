"""Automatic hiring module for the digital company.

Provides the :class:`ModuloRH` used to create and allocate new agents when
there is available balance and unmet demand or pending tasks.
"""

import logging
import random # Ensure random is imported
from typing import Dict, List # List for iterating over a copy

import state # Added
# import empresa_digital # No longer needed as selecionar_modelo and criar_agente are from agent_utils
from agent_utils import selecionar_modelo, criar_agente # Added

# Note: Agente type hint in comment was List[empresa_digital.Agente], now should be List[core_types.Agente]
# Actual usage is state.agentes.values() which refers to core_types.Agente correctly.
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
        if not state.MODO_VIDA_INFINITA:  # Only apply saldo logic if not in infinite mode # Use state
            if state.saldo <= 0: # Use state
                logger.info("Saldo insuficiente para contratações regulares.")
                state.registrar_evento("RH: saldo atual insuficiente para contratações regulares.") # Use state
                if state.tarefas_pendentes and len(state.agentes) < 2 and random.random() < 0.1:  # 10% chance # Use state
                    state.saldo += 20.0 # Emergency fund # Use state
                    state.registrar_evento( # Use state
                        "RH: Fundo de emergência (20.0) ativado para garantir operações mínimas devido a tarefas pendentes e poucos agentes."
                    )
                    logger.info("RH: Fundo de emergência de 20.0 ativado. Saldo atual: %s", state.saldo) # Use state

                if state.saldo <= 0: # Use state
                    logger.info("Saldo ainda insuficiente após verificação de emergência, nenhuma contratação realizada.")
                    state.registrar_evento("RH: saldo ainda insuficiente após verificação de emergência.") # Use state
                    return
        else:  # In MODO_VIDA_INFINITA
            state.registrar_evento( # Use state
                "RH: MODO VIDA INFINITA ATIVO - Restrições de saldo ignoradas para contratação."
            )
            logger.info("RH: MODO VIDA INFINITA ATIVO - Restrições de saldo ignoradas para contratação.")
            # Optionally ensure saldo is very high for any logic downstream that might still check it.
            if state.saldo < 1000: # Ensure a high baseline for any other checks # Use state
                state.saldo = 10000.0 # Use state
                state.registrar_evento("RH: MODO VIDA INFINITA - Saldo artificialmente elevado para 10000.") # Use state

        contratou = False

        # Verifica cada sala com carencia de agentes
        for local in sorted(state.locais.values(), key=lambda l: l.nome): # Use state
            if len(local.agentes_presentes) < self.min_por_sala and state.tarefas_pendentes: # Use state
                nome = self._novo_nome()
                modelo, motivo = selecionar_modelo("Funcionario") # Use from agent_utils
                criar_agente(nome, "Funcionario", modelo, local.nome) # Use from agent_utils
                msg = f"RH contratou {nome} para {local.nome} - {motivo}"
                logger.info(
                    "Novo agente %s alocado em %s por falta de pessoal - %s",
                    nome,
                    local.nome,
                    motivo,
                )
                state.registrar_evento(msg) # Use state
                contratou = True

        # Conta agentes por funcao
        contagem_funcao: Dict[str, int] = {}
        for ag in state.agentes.values(): # Use state
            contagem_funcao[ag.funcao] = contagem_funcao.get(ag.funcao, 0) + 1
        for funcao, qtd in contagem_funcao.items():
            if qtd < self.min_por_funcao and state.tarefas_pendentes: # Use state
                nome = self._novo_nome()
                primeiro_local = min(state.locais.values(), key=lambda l: l.nome, default=None) # Use state
                if primeiro_local:
                    modelo, motivo = selecionar_modelo(funcao) # Use from agent_utils
                    criar_agente(nome, funcao, modelo, primeiro_local.nome) # Use from agent_utils
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
                    state.registrar_evento(msg) # Use state
                    contratou = True

        # Cria agentes para tarefas pendentes (agora `state.tarefas_pendentes` contém objetos Task)
        while state.tarefas_pendentes: # Use state
            tarefa_obj = state.tarefas_pendentes.pop(0) # Pop um objeto Task # Use state

            # Processar apenas tarefas que estão "todo" para criação de novos agentes.
            # Tarefas "in_progress" ou "done" não deveriam estar aqui para contratação.
            # Se uma tarefa "in_progress" está aqui, significa que o agente anterior pode ter sido removido.
            # Por ora, vamos focar em criar agentes para tarefas "todo".
            # Se uma tarefa já está "in_progress", não deveríamos criar um novo agente para ela aqui,
            # a menos que a lógica de reatribuição seja explicitamente desejada no RH.
            # Para o escopo atual, apenas tarefas "todo" devem gerar novos agentes.
            if tarefa_obj.status != "todo":
                logger.warning(f"RH encontrou tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) com status '{tarefa_obj.status}' na fila de pendências. Esperado 'todo'. Tarefa será devolvida à fila.")
                state.tarefas_pendentes.insert(0, tarefa_obj) # Devolve ao início da fila para evitar loop infinito se for sempre a primeira # Use state
                # Ou considerar uma lista separada para tarefas problemáticas.
                # Para evitar loops, se a primeira tarefa não for 'todo', podemos parar de processar neste ciclo.
                if state.tarefas_pendentes[0].status != "todo": # Se a primeira ainda não é 'todo' # Use state
                    break # Evita processar a mesma tarefa não 'todo' repetidamente.
                continue


            primeiro_local_obj = min(state.locais.values(), key=lambda l: l.nome, default=None) # Use state
            if not primeiro_local_obj:
                logger.error("Não há locais definidos. Impossível criar novo Executor para a tarefa. Devolvendo tarefa à fila.")
                state.tarefas_pendentes.insert(0, tarefa_obj) # Devolve a tarefa ao início da fila # Use state
                break # Interrompe o loop de criação de agentes para tarefas se não há locais

            novo_executor_nome = self._novo_nome()
            modelo_llm_executor, motivo_modelo = selecionar_modelo("Executor", f"Executar tarefa: {tarefa_obj.description}") # Use from agent_utils

            try:
                # Atualizar status da tarefa para "in_progress" ANTES de criar o agente
                # A mensagem de log aqui é importante para rastrear quem foi designado.
                tarefa_obj.update_status("in_progress", f"Atribuída ao novo agente {novo_executor_nome} a ser criado.")
                logger.info(f"Tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) status atualizado para 'in_progress'.")
                state.registrar_evento(f"Tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) status: in_progress, sendo atribuída a {novo_executor_nome}.") # Use state

                novo_executor = criar_agente( # Use from agent_utils
                    nome=novo_executor_nome,
                    funcao="Executor",
                    modelo_llm=modelo_llm_executor,
                    local=primeiro_local_obj.nome, # Nome do local
                    objetivo=f"task_id:{tarefa_obj.id}" # Definir objetivo com o ID da tarefa
                )
                # Log após criação bem sucedida do agente
                msg = f"RH criou Executor '{novo_executor.nome}' para tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}). Motivo LLM: {motivo_modelo}"
                logger.info(msg)
                state.registrar_evento(msg) # Use state
                contratou = True
            except ValueError as e: # Erro ao criar agente
                logger.error(f"Falha ao criar novo Executor '{novo_executor_nome}' para a tarefa '{tarefa_obj.description}': {e}")
                # Reverter status da tarefa para "todo"
                tarefa_obj.update_status("todo", f"Criação do agente {novo_executor_nome} falhou. Retornando para 'todo'.")
                logger.warning(f"Status da tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) revertido para 'todo' devido à falha na criação do agente.")
                state.registrar_evento(f"Falha ao criar agente para tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}). Status revertido para 'todo'.") # Use state
                state.tarefas_pendentes.insert(0, tarefa_obj) # Devolve a tarefa ao início da fila # Use state
            except Exception as e_geral: # Outros erros inesperados
                logger.error(f"Erro inesperado ao tentar criar agente para tarefa '{tarefa_obj.description}': {e_geral}", exc_info=True)
                # Tentar reverter status se possível, ou logar inconsistência
                if tarefa_obj.status == "in_progress": # Se o status foi mudado
                    tarefa_obj.update_status("todo", f"Erro crítico na criação do agente {novo_executor_nome}. Retornando para 'todo'.")
                    logger.warning(f"Status da tarefa '{tarefa_obj.description}' (ID: {tarefa_obj.id}) revertido para 'todo' devido a erro crítico.")
                state.tarefas_pendentes.insert(0, tarefa_obj) # Devolve a tarefa # Use state

        if not contratou:
            logger.info("Nenhuma contratacao necessaria neste ciclo")
            state.registrar_evento("RH: nenhuma contratacao necessaria") # Use state

        # --- Logic for Incrementing Idle Cycles and Optional Layoff/Role Change for Executors ---
        logger.info("RH: Verificando ociosidade de Executores...")
        agentes_para_remover: List[Agente] = [] # Store agents to be dismissed # Agente is from core_types

        # First, increment idle cycles or reset them
        for agente in state.agentes.values(): # Use state
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
        # Iterate over a copy of values for safe removal from state.agentes if needed
        for agente in list(state.agentes.values()): # Use state
            if agente.funcao.lower() == "executor" and agente.cycles_idle >= 5:
                if random.random() < 0.5:  # 50% chance to dismiss
                    agentes_para_remover.append(agente)
                    logger.info(f"RH: Executor ocioso {agente.nome} selecionado para dispensa após {agente.cycles_idle} ciclos.")
                    state.registrar_evento(f"RH: Executor {agente.nome} selecionado para dispensa por ociosidade ({agente.cycles_idle} ciclos).") # Use state
                else: # Other 50% chance to redefine role
                    old_funcao = agente.funcao
                    agente.funcao = "Funcionario" # Generic role
                    agente.objetivo_atual = "Aguardando novas diretrizes como Funcionario."
                    agente.cycles_idle = 0  # Reset idle counter
                    logger.info(f"RH: Executor ocioso {agente.nome} teve função redefinida para 'Funcionario' após {agente.cycles_idle} ciclos.")
                    state.registrar_evento(f"RH: Executor {agente.nome} redefinido para 'Funcionario' por ociosidade ({agente.cycles_idle} ciclos). Antiga função: {old_funcao}.") # Use state

        # Perform removals
        if agentes_para_remover:
            logger.info(f"RH: Processando dispensa de {len(agentes_para_remover)} Executores ociosos.")
        for agente_a_remover in agentes_para_remover:
            if agente_a_remover.local_atual:
                agente_a_remover.local_atual.remover_agente(agente_a_remover)
                logger.debug(f"Executor {agente_a_remover.nome} removido do local {agente_a_remover.local_atual.nome}.")

            if agente_a_remover.nome in state.agentes: # Use state
                del state.agentes[agente_a_remover.nome] # Use state
                logger.info(f"Executor {agente_a_remover.nome} efetivamente dispensado e removido do sistema.")
                state.registrar_evento(f"DISPENSA: Executor {agente_a_remover.nome} removido do sistema por ociosidade.") # Use state
            else:
                logger.warning(f"RH: Tentativa de dispensar {agente_a_remover.nome}, mas não encontrado em state.agentes (pode já ter sido removido).") # Use state


modulo_rh = ModuloRH()
