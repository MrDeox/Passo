from typing import Any, Optional
from .base_agent import BaseAgent

class ExecutionAgent(BaseAgent):
    """
    Agente responsável por executar tarefas concretas (ex: desenvolver um produto).
    """
    def __init__(self, name: str, company_state: Any, llm_integration: Any, llm_model: Optional[str] = "default_execution_model"):
        super().__init__(name, "ExecutionAgent", llm_model, company_state, llm_integration)

    async def perform_task(self) -> Any:
        """
        Executa a tarefa atribuída (ex: desenvolver um protótipo de uma ideia validada).
        """
        # Exemplo: Obter uma tarefa de execução (a ser implementado em CompanyState ou Workflows)
        # execution_task = self.company_state.get_task_for_execution(assignee=self.name)
        execution_task = {"id": "task123", "type": "develop_prototype", "details": "Desenvolver protótipo para Ideia Alpha", "idea_name": "Ideia Alpha"} # Exemplo
        self.current_task = execution_task

        if not self.current_task:
            print(f"{self.name} não tem tarefas de execução atribuídas.")
            self.update_history("execute_task", {"status": "no_task_assigned"})
            return None

        prompt = f"Você precisa executar a seguinte tarefa: {self.current_task['details']}. Descreva os passos principais que você tomaria e um resultado esperado."

        execution_plan_text = await self.send_prompt_to_llm(prompt)

        # Em uma implementação real, o agente poderia gerar código, artefatos, etc.
        # e atualizar o status da tarefa no company_state.
        simulated_result = f"Protótipo para '{self.current_task['idea_name']}' parcialmente desenvolvido. Passos: ..." # Exemplo

        self.update_history("execute_task", {"task_id": self.current_task['id'], "plan_text": execution_plan_text, "simulated_result": simulated_result})

        # Exemplo: Atualizar tarefa no estado da empresa (a ser implementado em CompanyState)
        # self.company_state.update_task_progress(task_id=self.current_task['id'], progress_update=simulated_result, status="in_progress")

        print(f"{self.name} está executando a tarefa '{self.current_task['details']}'. Resultado simulado: {simulated_result}")
        # Se a tarefa for concluída:
        # self.company_state.update_task_progress(task_id=self.current_task['id'], progress_update="Concluído", status="completed")
        # self.current_task = None
        return simulated_result
