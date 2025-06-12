from typing import Any, Optional
from .base_agent import BaseAgent

class CECAgent(BaseAgent): # Chief Executive Creative Agent
    """
    Agente principal que supervisiona, define estratégias e coordena outros agentes.
    Combina funções de CEO e direcionador criativo.
    """
    def __init__(self, name: str, company_state: Any, llm_integration: Any, llm_model: Optional[str] = "default_strategic_model"):
        super().__init__(name, "CECAgent", llm_model, company_state, llm_integration)

    async def perform_task(self) -> Any:
        """
        Analisa o estado geral da empresa e define diretrizes ou tarefas de alto nível.
        """
        # Exemplo: Obter um resumo do estado da empresa (a ser implementado)
        # company_summary = self.company_state.get_overall_summary()
        company_summary = {
            "total_ideas": 10, "ideas_validated": 5, "products_launched": 2,
            "active_services": 1, "current_balance": 15000,
            "recent_feedbacks": ["Produto X é bom", "Serviço Y demorou"],
            "pending_tasks_count": 3
        }

        prompt = f"Você é o CEC (Chief Executive Creative Agent). Analise o seguinte resumo da empresa: {company_summary}. Defina 1-2 prioridades estratégicas para o próximo ciclo e, se necessário, atribua uma tarefa específica a um tipo de agente (Creative, Validation, Execution, Marketing, Financial)."

        strategic_decision_text = await self.send_prompt_to_llm(prompt)

        # Em uma implementação real, parsearíamos a decisão e criaríamos tarefas,
        # enviaríamos feedback para outros agentes, ou ajustaríamos parâmetros no company_state.
        parsed_decision = {
            "priorities": ["Aumentar validação de ideias", "Melhorar marketing do Produto X"],
            "new_task_for_agent_type": {"type": "MarketingAgent", "task_description": "Criar nova campanha para Produto X"}
        } # Exemplo

        self.update_history("strategic_decision", {"raw_text": strategic_decision_text, "parsed_decision": parsed_decision})

        # Exemplo: Criar tarefa ou enviar feedback (a ser implementado)
        # if "new_task_for_agent_type" in parsed_decision:
        #     task_info = parsed_decision["new_task_for_agent_type"]
        #     self.company_state.add_task(description=task_info["task_description"], assigned_role=task_info["type"], created_by=self.name)

        print(f"{self.name} (CEC) definiu prioridades: {parsed_decision['priorities']}.")
        if "new_task_for_agent_type" in parsed_decision:
            print(f"CEC atribuiu nova tarefa: {parsed_decision['new_task_for_agent_type']}")

        return parsed_decision
