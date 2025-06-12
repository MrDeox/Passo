from typing import Any, Optional, Dict, List
from enum import Enum
from .base_workflow import BaseWorkflow, WorkflowStatus
# from src.core.idea import Idea, IdeaStatus
# from src.agents.creative_agent import CreativeAgent
# from src.agents.validation_agent import ValidationAgent

class IdeationWorkflow(BaseWorkflow):
    """
    Gerencia o processo de geração, submissão e validação inicial de ideias.
    """
    def __init__(self, workflow_id: str, company_state: Any, settings: Optional[Dict] = None):
        super().__init__(workflow_id, company_state, settings)
        self.num_ideas_to_generate = settings.get("num_ideas_to_generate", 3) if settings else 3
        self.generated_idea_ids: List[str] = []

    async def run(self) -> bool:
        self._set_status(WorkflowStatus.RUNNING, "Iniciando workflow de ideação.")

        # Passo 1: Geração de Ideias
        self._log_step("idea_generation", "Iniciando geração de ideias.")

        print(f"IdeationWorkflow: Simulando CreativeAgent para gerar {self.num_ideas_to_generate} ideias.")
        # Mock de ideias geradas
        from src.core.idea import Idea, IdeaStatus # Import local
        for i in range(self.num_ideas_to_generate):
            new_idea = Idea(
                name=f"Ideia Simulada {self.workflow_id}-{i+1}",
                description=f"Descrição da ideia simulada {i+1} gerada pelo workflow {self.workflow_id}.",
                author_agent_name="CreativeAgent_Simulated"
            )
            self.company_state.add_idea(new_idea)
            self.generated_idea_ids.append(new_idea.id)
            self._log_step("idea_generated", f"Ideia '{new_idea.name}' (ID: {new_idea.id}) gerada e adicionada.", {"idea_id": new_idea.id})

        if not self.generated_idea_ids:
            self._set_status(WorkflowStatus.FAILED, "Nenhuma ideia foi gerada.")
            return False

        # Passo 2: Validação das Ideias Geradas (simplificado)
        self._log_step("idea_validation_start", "Iniciando validação das ideias geradas.")
        for idea_id in self.generated_idea_ids:
            idea = self.company_state.get_idea(idea_id)
            if idea:
                idea.update_status(IdeaStatus.VALIDATING, {"workflow_id": self.workflow_id})

                print(f"IdeationWorkflow: Simulando ValidationAgent para a ideia '{idea.name}'.")
                # Mock de resultado da validação
                validation_outcome = IdeaStatus.VALIDATED_APPROVED
                validation_details = {"score": 7, "comments": "Parece razoável (simulado).", "validator_agent": "ValidationAgent_Simulated"}
                idea.validation_details = validation_details
                idea.update_status(validation_outcome, validation_details)
                self.company_state.log_event("IDEA_VALIDATED", f"Ideia '{idea.name}' validada como {validation_outcome.value}", {"idea_id": idea.id, **validation_details})
                self._log_step("idea_validated", f"Ideia '{idea.name}' validada como {validation_outcome.value}.", {"idea_id": idea.id, "status": validation_outcome.value})
            else:
                self._log_step("validation_error", f"Ideia com ID {idea_id} não encontrada para validação.", {"idea_id": idea_id}, level="warning")

        self._set_status(WorkflowStatus.COMPLETED, "Workflow de ideação concluído.")
        return True
