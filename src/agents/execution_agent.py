import json
from typing import Any, Optional, List, Dict
from .base_agent import BaseAgent
from src.core.task import Task, TaskStatus
from src.core.idea import Idea # Para buscar detalhes da ideia

class ExecutionAgent(BaseAgent):
    """
    Agente responsável pelo planejamento detalhado de tarefas de execução.
    A "execução" real da tarefa (ex: desenvolvimento de código) é simulada ou feita por outro sistema.
    Este agente foca em criar o plano de execução.
    """
    def __init__(self, name: str, company_state: Any, llm_integration: Any, llm_model: Optional[str] = "default_execution_model"):
        super().__init__(name, "ExecutionAgent", llm_model, company_state, llm_integration) # Role é "ExecutionAgent"

    async def perform_task(self) -> Optional[Dict]:
        """
        Busca uma tarefa PENDENTE atribuída ao ExecutionAgent, gera um plano de execução para ela usando LLM,
        e atualiza a tarefa com o plano e status COMPLETED (planejamento concluído).
        """
        pending_tasks: List[Task] = self.company_state.get_pending_tasks_for_role(self.role)

        if not pending_tasks:
            print(f"{self.name} ({self.role}): Nenhuma tarefa pendente encontrada para planejamento.")
            self.update_history("planning_task_search", {"status": "no_pending_tasks_found"})
            return None

        task_to_plan: Task = pending_tasks[0] # Pega a primeira tarefa pendente
        self.current_task = task_to_plan

        print(f"{self.name}: Iniciando planejamento para a tarefa ID {task_to_plan.id} ('{task_to_plan.name}').")

        task_to_plan.update_status(
            TaskStatus.IN_PROGRESS,
            {"planner_agent_name": self.name, "action": "Starting task planning"},
            agent_name=self.name
        )
        self.update_history("task_planning_started", {"task_id": task_to_plan.id, "task_name": task_to_plan.name})

        task_details = task_to_plan.description
        idea_info = ""
        if task_to_plan.related_item_type == "Idea" and task_to_plan.related_item_id:
            idea = self.company_state.get_idea(task_to_plan.related_item_id)
            if idea:
                idea_info = (f"A tarefa está relacionada à Ideia: '{idea.name}' "
                             f"(Descrição: {idea.description}, Público-Alvo: {idea.target_audience}). "
                             f"Status atual da ideia: {idea.status.value}. "
                             f"Detalhes da validação da ideia: {idea.validation_details}")

        prompt = f"""
        Você é um assistente de planejamento de projetos experiente. Sua tarefa é criar um plano detalhado para a seguinte solicitação:

        Nome da Tarefa: {task_to_plan.name}
        Descrição da Tarefa: {task_details}
        {idea_info}

        Por favor, gere o seguinte:
        1. "plan_steps": Uma lista de passos de execução claros, concisos e acionáveis para completar esta tarefa. Divida em etapas lógicas.
        2. "required_resources": Uma lista dos principais recursos necessários (ex: "Desenvolvedor Python Pleno", "Acesso à API X", "Banco de dados PostgreSQL").
        3. "potential_challenges": Uma lista de 2-3 potenciais desafios ou obstáculos e sugestões breves de como mitigá-los.
        4. "estimated_duration_short_summary": Um resumo textual breve da duração estimada para completar esta tarefa (ex: "alguns dias de trabalho focado", "1-2 semanas", "aproximadamente X horas de desenvolvimento").

        Retorne a resposta como uma string JSON formatada como um único objeto com as chaves "plan_steps", "required_resources", "potential_challenges", e "estimated_duration_short_summary".
        Exemplo de formato:
        {{
            "plan_steps": ["Definir o esquema do banco de dados.", "Desenvolver os endpoints da API.", "Escrever testes unitários.", "Implantar a aplicação."],
            "required_resources": ["Desenvolvedor Backend", "Banco de Dados (ex: SQLite para protótipo)", "Ferramenta de Testes (ex: PyTest)"],
            "potential_challenges": ["A integração com a API externa X pode ser complexa. Mitigação: Alocar tempo extra para pesquisa e testes de integração.", "Requisitos podem mudar. Mitigação: Manter comunicação constante com o solicitante."],
            "estimated_duration_short_summary": "Aproximadamente 3-5 dias de desenvolvimento."
        }}
        """

        raw_plan_text = await self.send_prompt_to_llm(prompt)
        parsed_plan: Optional[Dict] = None

        if not raw_plan_text or raw_plan_text.startswith("Erro") or raw_plan_text.startswith("Resposta mockada"):
            error_detail = f"Resposta inválida ou de erro do LLM para planejamento da tarefa {task_to_plan.id}: {raw_plan_text}"
            print(f"{self.name}: {error_detail}")
            self.update_history("task_planning_error", {"task_id": task_to_plan.id, "error": "LLMResponseInvalid", "details": error_detail, "raw_response": raw_plan_text})
            task_to_plan.update_status(TaskStatus.FAILED, {"error": "LLMResponseInvalid", "details": error_detail, "planner_agent_name": self.name}, agent_name=self.name)
            self.current_task = None
            return None

        try:
            # Limpeza básica da resposta do LLM
            if raw_plan_text.strip().startswith("```json"):
                raw_plan_text = raw_plan_text.strip()[7:-3].strip()
            elif raw_plan_text.strip().startswith("```"):
                 raw_plan_text = raw_plan_text.strip()[3:-3].strip()

            parsed_plan = json.loads(raw_plan_text)
            if not isinstance(parsed_plan, dict): # Garantir que é um dicionário
                 raise ValueError("A resposta do LLM não foi um objeto JSON (dicionário).")


        except json.JSONDecodeError as e:
            error_detail = f"Falha ao decodificar JSON do plano da tarefa {task_to_plan.id}: {e}. Resposta: {raw_plan_text[:500]}"
            print(f"{self.name}: {error_detail}")
            self.update_history("task_planning_error", {"task_id": task_to_plan.id, "error": "JSONDecodeError", "details": str(e), "raw_response_snippet": raw_plan_text[:500]})
            task_to_plan.update_status(TaskStatus.FAILED, {"error": "JSONDecodeError", "details": str(e), "planner_agent_name": self.name, "raw_response_snippet": raw_plan_text[:500]}, agent_name=self.name)
            self.current_task = None
            return None
        except Exception as e: # Outras exceções, incluindo ValueError de cima
            error_detail = f"Erro inesperado ao processar plano da tarefa {task_to_plan.id}: {e}. Resposta: {raw_plan_text[:500]}"
            print(f"{self.name}: {error_detail}")
            self.update_history("task_planning_error", {"task_id": task_to_plan.id, "error": "GenericProcessingException", "details": str(e), "raw_response_snippet": raw_plan_text[:500]})
            task_to_plan.update_status(TaskStatus.FAILED, {"error": "GenericProcessingException", "details": str(e), "planner_agent_name": self.name, "raw_response_snippet": raw_plan_text[:500]}, agent_name=self.name)
            self.current_task = None
            return None

        if parsed_plan:
            task_to_plan.result = parsed_plan # Armazena o plano completo no campo 'result' da tarefa

            plan_summary = f"{len(parsed_plan.get('plan_steps',[]))} passos; {len(parsed_plan.get('required_resources',[]))} recursos; {len(parsed_plan.get('potential_challenges',[]))} desafios."
            status_details = {
                "planner_agent_name": self.name,
                "action": "Planning completed successfully",
                "plan_summary": plan_summary,
                "estimated_duration": parsed_plan.get("estimated_duration_short_summary", "N/A")
            }
            task_to_plan.update_status(TaskStatus.COMPLETED, status_details, agent_name=self.name)

            self.update_history("task_planning_completed", {"task_id": task_to_plan.id, "task_name": task_to_plan.name, "generated_plan_summary": plan_summary})
            print(f"{self.name}: Planejamento para a tarefa '{task_to_plan.name}' (ID: {task_to_plan.id}) concluído. Plano gerado com {plan_summary}")
            self.current_task = None
            return parsed_plan

        # Fallback, caso algo muito inesperado aconteça
        self.update_history("task_planning_failed_unexpectedly", {"task_id": task_to_plan.id, "raw_response": raw_plan_text})
        task_to_plan.update_status(TaskStatus.FAILED, {"error": "UnknownPlanningFailure", "planner_agent_name": self.name}, agent_name=self.name)
        self.current_task = None
        return None
