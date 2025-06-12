from typing import Any, Optional
from .base_agent import BaseAgent

class ValidationAgent(BaseAgent):
    """
    Agente responsável por validar a viabilidade e o potencial de ideias.
    """
    def __init__(self, name: str, company_state: Any, llm_integration: Any, llm_model: Optional[str] = "default_validation_model"):
        super().__init__(name, "ValidationAgent", llm_model, company_state, llm_integration)

    async def perform_task(self) -> Any:
        """
        Valida uma ideia pendente do company_state.
        """
        # Exemplo: Obter uma ideia pendente (a ser implementado em CompanyState)
        # pending_idea = self.company_state.get_pending_idea_for_validation()
        pending_idea = {"name": "Ideia Alpha", "description": "Descrição Alpha para validar", "author": "CreativeAgent1"} # Exemplo

        if not pending_idea:
            print(f"{self.name} não encontrou ideias para validar.")
            self.update_history("validate_idea", {"status": "no_ideas_found"})
            return None

        prompt = f"Avalie a seguinte ideia de produto/serviço: Nome: {pending_idea['name']}, Descrição: {pending_idea['description']}. Forneça uma pontuação de viabilidade (0-10), uma pontuação de potencial de mercado (0-10) e uma breve justificativa para cada."

        validation_result_text = await self.send_prompt_to_llm(prompt)

        # Em uma implementação real, parsearíamos validation_result_text
        # e atualizaríamos o status da ideia no company_state.
        parsed_validation = {"viability_score": 8, "market_potential_score": 7, "justification": "Parece promissor."} # Exemplo

        self.update_history("validate_idea", {"idea_name": pending_idea['name'], "raw_text": validation_result_text, "parsed_validation": parsed_validation})

        # Exemplo: Atualizar ideia no estado da empresa (a ser implementado em CompanyState)
        # self.company_state.update_idea_validation(idea_id=pending_idea['id'], validation_data=parsed_validation, validator_name=self.name)

        print(f"{self.name} validou a ideia '{pending_idea['name']}' com os seguintes resultados: {parsed_validation}")
        return parsed_validation
