import json
from typing import Any, Optional, List, Dict
from .base_agent import BaseAgent
from src.core.idea import Idea, IdeaStatus

class ValidationAgent(BaseAgent):
    """
    Agente responsável por validar a viabilidade e o potencial de ideias.
    """
    def __init__(self, name: str, company_state: Any, llm_integration: Any, llm_model: Optional[str] = "default_validation_model"):
        super().__init__(name, "ValidationAgent", llm_model, company_state, llm_integration)

    async def perform_task(self) -> Optional[Dict]:
        """
        Valida uma ideia com status PROPOSED do company_state usando LLM.
        """
        idea_to_validate: Optional[Idea] = None
        for idea in self.company_state.ideas.values():
            if idea.status == IdeaStatus.PROPOSED:
                idea_to_validate = idea
                break # Pega a primeira ideia PROPOSED encontrada

        if not idea_to_validate:
            print(f"{self.name}: Nenhuma ideia com status 'PROPOSED' encontrada para validação.")
            self.update_history("validate_idea_search", {"status": "no_proposed_ideas_found"})
            return None

        print(f"{self.name}: Iniciando validação da ideia ID {idea_to_validate.id} ('{idea_to_validate.name}').")

        original_status_details = idea_to_validate.status_history[-1] if idea_to_validate.status_history else {}
        idea_to_validate.update_status(
            IdeaStatus.VALIDATING,
            {"validator_agent_name": self.name, "previous_status_details": original_status_details}
        )
        self.update_history("idea_validation_started", {"idea_id": idea_to_validate.id, "idea_name": idea_to_validate.name})

        initial_potential_analysis = idea_to_validate.validation_details.get("llm_potential_analysis", "N/A")

        prompt = f"""
        Por favor, analise a seguinte ideia de produto/serviço digital:
        Nome da Ideia: {idea_to_validate.name}
        Descrição: {idea_to_validate.description}
        Público-Alvo: {idea_to_validate.target_audience}
        Análise de Potencial Inicial (fornecida pelo agente criativo): {initial_potential_analysis}

        Realize uma análise de validação e forneça os seguintes campos:
        - "viability_score": Um score de 0 a 10 para a viabilidade técnica e de execução da ideia.
        - "market_potential_score": Um score de 0 a 10 para o potencial de mercado da ideia.
        - "risk_analysis": Uma descrição concisa dos principais riscos associados (técnicos, de mercado, financeiros).
        - "improvement_suggestions": Sugestões específicas para melhorar a ideia ou mitigar riscos.
        - "final_recommendation": Sua recomendação final. Deve ser uma das seguintes strings: "APPROVE", "REJECT", "REVIEW".

        Retorne a resposta como uma string JSON formatada como um único objeto com os campos acima.
        Exemplo de formato:
        {{
            "viability_score": 8,
            "market_potential_score": 7,
            "risk_analysis": "O principal risco é a alta competição no mercado X...",
            "improvement_suggestions": "Considerar focar em um nicho específico Y para reduzir a competição inicial.",
            "final_recommendation": "APPROVE"
        }}
        """

        raw_validation_text = await self.send_prompt_to_llm(prompt)
        parsed_validation_result: Optional[Dict] = None

        if not raw_validation_text or raw_validation_text.startswith("Erro") or raw_validation_text.startswith("Resposta mockada"):
            error_detail = f"Resposta inválida ou de erro do LLM: {raw_validation_text}"
            print(f"{self.name}: {error_detail}")
            self.update_history("validate_idea_error", {"idea_id": idea_to_validate.id, "error": "LLMResponseInvalid", "details": error_detail, "raw_response": raw_validation_text})
            idea_to_validate.update_status(IdeaStatus.PROPOSED, {"validation_error": "LLMResponseInvalid", "details": error_detail, "validator_agent_name": self.name})
            return None

        try:
            # Tenta remover possíveis ```json ... ``` ou ``` ... ``` que o LLM possa adicionar
            if raw_validation_text.strip().startswith("```json"):
                raw_validation_text = raw_validation_text.strip()[7:-3].strip()
            elif raw_validation_text.strip().startswith("```"):
                raw_validation_text = raw_validation_text.strip()[3:-3].strip()

            parsed_validation_result = json.loads(raw_validation_text)

            if not isinstance(parsed_validation_result, dict): # Checa se é um dicionário
                error_detail = f"Resposta do LLM não é um dicionário JSON como esperado. Resposta: {raw_validation_text}"
                raise ValueError(error_detail)


        except json.JSONDecodeError as e:
            error_detail = f"Falha ao decodificar JSON da resposta do LLM: {e}. Resposta: {raw_validation_text[:500]}"
            print(f"{self.name}: {error_detail}")
            self.update_history("validate_idea_error", {"idea_id": idea_to_validate.id, "error": "JSONDecodeError", "details": str(e), "raw_response_snippet": raw_validation_text[:500]})
            idea_to_validate.update_status(IdeaStatus.PROPOSED, {"validation_error": "JSONDecodeError", "details": str(e), "validator_agent_name": self.name, "raw_response_snippet": raw_validation_text[:500]})
            return None
        except Exception as e: # Inclui o ValueError de cima e outros genéricos
            error_detail = f"Erro inesperado ao processar validação do LLM: {e}. Resposta: {raw_validation_text[:500]}"
            print(f"{self.name}: {error_detail}")
            self.update_history("validate_idea_error", {"idea_id": idea_to_validate.id, "error": "GenericProcessingException", "details": str(e), "raw_response_snippet": raw_validation_text[:500]})
            idea_to_validate.update_status(IdeaStatus.PROPOSED, {"validation_error": "GenericProcessingException", "details": str(e), "validator_agent_name": self.name, "raw_response_snippet": raw_validation_text[:500]})
            return None

        if parsed_validation_result:
            # Garantir que os campos esperados existam, mesmo que com valores default
            viability_score = parsed_validation_result.get("viability_score", 0)
            market_potential_score = parsed_validation_result.get("market_potential_score", 0)
            risk_analysis = parsed_validation_result.get("risk_analysis", "N/A")
            improvement_suggestions = parsed_validation_result.get("improvement_suggestions", "N/A")
            final_recommendation = parsed_validation_result.get("final_recommendation", "REVIEW").upper() # Normaliza para maiúsculas

            # Atualizar validation_details da ideia
            current_validation_details = {
                "validator_agent_name": self.name,
                "validation_timestamp": self.company_state.current_time, # Supondo que company_state tem current_time
                "viability_score": viability_score,
                "market_potential_score": market_potential_score,
                "risk_analysis": risk_analysis,
                "improvement_suggestions": improvement_suggestions,
                "llm_recommendation": final_recommendation
            }
            # Adiciona ao invés de sobrescrever totalmente, para manter llm_potential_analysis
            idea_to_validate.validation_details.update(current_validation_details)


            new_status: IdeaStatus
            if final_recommendation == "APPROVE":
                new_status = IdeaStatus.VALIDATED_APPROVED
            elif final_recommendation == "REJECT":
                new_status = IdeaStatus.VALIDATED_REJECTED
            elif final_recommendation == "REVIEW":
                new_status = IdeaStatus.PROPOSED # Reverte para PROPOSED para revisão (ou um novo status NEEDS_MANUAL_REVIEW)
                idea_to_validate.validation_details["review_reason"] = "LLM recomendou revisão."
            else: # Recomendação não reconhecida
                new_status = IdeaStatus.PROPOSED
                idea_to_validate.validation_details["review_reason"] = f"Recomendação não reconhecida do LLM: {final_recommendation}. Necessita revisão."
                print(f"{self.name}: Recomendação não reconhecida '{final_recommendation}' para a ideia ID {idea_to_validate.id}. Marcando para revisão.")

            idea_to_validate.update_status(new_status, idea_to_validate.validation_details)

            log_summary = {
                "idea_id": idea_to_validate.id,
                "idea_name": idea_to_validate.name,
                "llm_recommendation": final_recommendation,
                "final_status": new_status.value,
                "scores": {"viability": viability_score, "market": market_potential_score}
            }
            self.update_history("idea_validation_completed", log_summary)
            print(f"{self.name}: Validação da ideia '{idea_to_validate.name}' (ID: {idea_to_validate.id}) concluída. Recomendação: {final_recommendation} -> Status: {new_status.value}.")
            return parsed_validation_result # Retorna o dict completo da validação do LLM

        # Caso algo muito inesperado ocorra e parsed_validation_result não seja populado, mas não caia nos excepts
        # (embora a lógica atual deva cobrir isso)
        print(f"{self.name}: Validação da ideia '{idea_to_validate.name}' não produziu um resultado parseável, apesar de não ter gerado exceção explícita.")
        idea_to_validate.update_status(IdeaStatus.PROPOSED, {"validation_error": "UnknownParsingFailure", "validator_agent_name": self.name})
        return None
