from typing import Any, Optional, Dict, List
from .base_workflow import BaseWorkflow, WorkflowStatus
from src.core.idea import Idea, IdeaStatus # Garantir que Idea está importado também
from src.agents.creative_agent import CreativeAgent
from src.agents.validation_agent import ValidationAgent
from src.utils.llm_integration import LLMIntegration # Para type hint

class IdeationWorkflow(BaseWorkflow):
    """
    Gerencia o processo de geração e validação inicial de ideias usando CreativeAgent e ValidationAgent.
    """
    def __init__(self, workflow_id: str, company_state: Any, llm_integration: LLMIntegration, settings: Optional[Dict] = None):
        super().__init__(workflow_id, company_state, settings)
        self.llm_integration = llm_integration
        # self.num_ideas_to_generate = settings.get("num_ideas_to_generate", 3) if settings else 3 # CreativeAgent define isso internamente
        self.max_validations_per_run = self.settings.get("max_validations_per_workflow_run", 5) if settings else 5
        self.generated_ideas_count_this_run = 0
        self.validated_ideas_count_this_run = 0

    async def run(self) -> bool:
        self._set_status(WorkflowStatus.RUNNING, "Iniciando workflow de ideação.")

        # Passo 1: Geração de Ideias com CreativeAgent
        self._log_step("idea_generation_phase_start", "Iniciando fase de geração de ideias com CreativeAgent.")

        creative_agent = CreativeAgent(
            name=f"CreativeAgent_for_Workflow_{self.workflow_id}",
            company_state=self.company_state,
            llm_integration=self.llm_integration,
            # llm_model pode ser pego de self.settings.get("creative_agent_model") ou um padrão no agente
        )

        try:
            generated_ideas_list: List[Idea] = await creative_agent.perform_task()
            self.generated_ideas_count_this_run = len(generated_ideas_list)

            if not generated_ideas_list:
                self._log_step("idea_generation_phase_warning", "CreativeAgent não gerou novas ideias nesta execução.", level="warning")
                # Não necessariamente uma falha do workflow, pode não haver necessidade de mais ideias ou o agente decidiu não gerar.
            else:
                self._log_step("idea_generation_phase_success", f"{self.generated_ideas_count_this_run} ideias foram geradas pelo CreativeAgent.")

        except Exception as e:
            self._log_step("idea_generation_phase_error", f"Erro durante a execução do CreativeAgent: {e}", {"error": str(e)}, level="error")
            self._set_status(WorkflowStatus.FAILED, f"Falha na geração de ideias: {e}")
            return False

        # Passo 2: Validação de Ideias com ValidationAgent
        self._log_step("idea_validation_phase_start", "Iniciando fase de validação de ideias com ValidationAgent.")

        validation_agent = ValidationAgent(
            name=f"ValidationAgent_for_Workflow_{self.workflow_id}",
            company_state=self.company_state,
            llm_integration=self.llm_integration,
            # llm_model pode ser pego de self.settings.get("validation_agent_model") ou um padrão no agente
        )

        ideas_processed_by_validator = 0

        while True:
            proposed_ideas_exist = any(idea.status == IdeaStatus.PROPOSED for idea in self.company_state.ideas.values())
            if not proposed_ideas_exist:
                self._log_step("validation_phase_complete_no_proposed", "Nenhuma ideia PROPOSED restante para validação.")
                break

            if ideas_processed_by_validator >= self.max_validations_per_run:
                self._log_step("validation_phase_limit_reached", f"Limite de {self.max_validations_per_run} validações por execução do workflow atingido.")
                break

            self._log_step("validation_attempt", f"Tentando validar próxima ideia. Validações realizadas nesta execução: {ideas_processed_by_validator + 1}.")

            try:
                validation_result_dict: Optional[Dict] = await validation_agent.perform_task()
            except Exception as e:
                self._log_step("validation_agent_execution_error", f"Erro durante a execução do ValidationAgent: {e}", {"error": str(e)}, level="error")
                # Considerar se o workflow deve parar ou continuar tentando validar outras ideias. Por ora, paramos o loop de validação.
                break

            if validation_result_dict: # ValidationAgent processou uma ideia
                ideas_processed_by_validator += 1
                self.validated_ideas_count_this_run +=1
                # O ValidationAgent já loga os detalhes da sua execução e atualiza o company_state.
                # O Workflow pode adicionar um log sumário, se desejar.
                self._log_step("idea_validated_by_agent",
                               f"ValidationAgent processou uma ideia. Recomendação: {validation_result_dict.get('final_recommendation', 'N/A')}, "
                               f"Viabilidade: {validation_result_dict.get('viability_score', 'N/A')}, "
                               f"Potencial: {validation_result_dict.get('market_potential_score', 'N/A')}")
            else:
                # Se validation_result_dict for None, significa que o ValidationAgent não encontrou mais ideias PROPOSED
                # ou ocorreu um erro interno nele que o fez retornar None (ele mesmo deve ter logado e tratado).
                self._log_step("validation_agent_no_action", "ValidationAgent não processou uma nova ideia (pode não haver mais ideias PROPOSED ou ocorreu um erro interno no agente).")
                break # Sai do loop de validação, pois não há mais trabalho para este agente ou erro.

        self._log_step("validation_phase_summary", f"Fase de validação concluída. Total de ideias processadas pelo ValidationAgent nesta execução: {ideas_processed_by_validator}.")

        # Workflow concluído com sucesso se chegou até aqui, mesmo que nenhuma ideia tenha sido gerada ou validada (workflow executou sem erros).
        # A "falha" seria um erro inesperado durante a execução dos agentes.
        self._set_status(WorkflowStatus.COMPLETED,
                         f"Workflow de ideação concluído. Ideias geradas: {self.generated_ideas_count_this_run}. "
                         f"Ideias processadas na validação: {self.validated_ideas_count_this_run}.")
        return True
