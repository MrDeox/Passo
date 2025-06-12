import json
from typing import Any, Optional, List, Dict
from .base_agent import BaseAgent
from src.core.idea import Idea, IdeaStatus

class CreativeAgent(BaseAgent):
    """
    Agente responsável pela ideação de novos produtos e serviços.
    """
    def __init__(self, name: str, company_state: Any, llm_integration: Any, llm_model: Optional[str] = "default_creative_model"):
        super().__init__(name, "CreativeAgent", llm_model, company_state, llm_integration)

    async def perform_task(self) -> List[Idea]:
        """
        Gera novas ideias de produtos ou serviços usando LLM e as adiciona ao CompanyState.
        """
        num_ideas_to_generate = 3
        prompt = f"""
        Gere {num_ideas_to_generate} ideias inovadoras de produtos ou serviços digitais.
        Considere tendências atuais de Inteligência Artificial e oportunidades de mercado relevantes.
        Para cada ideia, forneça os seguintes campos:
        - "name": Nome conciso e impactante da ideia.
        - "description": Descrição detalhada da ideia, explicando sua proposta de valor e funcionamento.
        - "target_audience": O público-alvo principal para esta ideia.
        - "potential_analysis": Uma breve análise do potencial de mercado e inovação da ideia.

        Retorne a resposta como uma string JSON formatada como uma lista de objetos.
        Cada objeto na lista deve representar uma ideia e conter os campos "name", "description", "target_audience" e "potential_analysis".
        Exemplo de formato:
        [
            {{"name": "Nome da Ideia 1", "description": "Descrição detalhada 1...", "target_audience": "Público Alvo 1", "potential_analysis": "Análise 1..."}},
            {{"name": "Nome da Ideia 2", "description": "Descrição detalhada 2...", "target_audience": "Público Alvo 2", "potential_analysis": "Análise 2..."}}
        ]
        """

        raw_ideas_text = await self.send_prompt_to_llm(prompt)
        generated_ideas: List[Idea] = []

        if not raw_ideas_text or raw_ideas_text.startswith("Erro") or raw_ideas_text.startswith("Resposta mockada"): # Adicionado para tratar respostas de erro do LLM
            print(f"{self.name}: Não foi possível obter uma resposta válida do LLM para gerar ideias. Resposta: {raw_ideas_text}")
            self.update_history("generate_ideas_error", {"error": "LLMResponseInvalid", "details": "Resposta do LLM vazia, mockada ou indicando erro.", "raw_response": raw_ideas_text})
            return generated_ideas

        try:
            # Tenta remover possíveis ```json ... ``` ou ``` ... ``` que o LLM possa adicionar
            if raw_ideas_text.strip().startswith("```json"):
                raw_ideas_text = raw_ideas_text.strip()[7:-3].strip()
            elif raw_ideas_text.strip().startswith("```"):
                 raw_ideas_text = raw_ideas_text.strip()[3:-3].strip()

            parsed_llm_response = json.loads(raw_ideas_text)

            if not isinstance(parsed_llm_response, list):
                print(f"{self.name}: Resposta do LLM não é uma lista como esperado. Resposta: {raw_ideas_text}")
                self.update_history("generate_ideas_error", {"error": "LLMResponseFormatError", "details": "Resposta do LLM não é uma lista.", "raw_response": raw_ideas_text})
                return generated_ideas

            for idea_data in parsed_llm_response:
                if not isinstance(idea_data, dict):
                    print(f"{self.name}: Item na lista de ideias do LLM não é um dicionário. Item: {idea_data}")
                    self.update_history("generate_ideas_warning", {"warning": "LLMResponseItemFormatError", "details": "Item da lista não é um dicionário.", "item_data": idea_data})
                    continue # Pula este item problemático

                name = idea_data.get("name", "Ideia Sem Nome")
                description = idea_data.get("description", "Descrição não fornecida.")
                target_audience = idea_data.get("target_audience")
                potential_analysis = idea_data.get("potential_analysis")

                new_idea = Idea(
                    name=name,
                    description=description,
                    target_audience=target_audience,
                    author_agent_name=self.name,
                    # status é definido por padrão em Idea como PENDING_VALIDATION
                    validation_details={"llm_potential_analysis": potential_analysis}
                )
                self.company_state.add_idea(new_idea)
                generated_ideas.append(new_idea)
                print(f"{self.name} gerou a ideia: '{new_idea.name}' (Status: {new_idea.status.value})")

        except json.JSONDecodeError as e:
            error_detail = f"Falha ao decodificar JSON da resposta do LLM: {e}. Resposta recebida: {raw_ideas_text[:500]}..." # Limita o tamanho da raw_response no log
            print(f"{self.name}: {error_detail}")
            self.update_history("generate_ideas_error", {"error": "JSONDecodeError", "details": str(e), "raw_response_snippet": raw_ideas_text[:500]})
        except Exception as e:
            error_detail = f"Erro inesperado ao processar ideias do LLM: {e}. Resposta recebida: {raw_ideas_text[:500]}..."
            print(f"{self.name}: {error_detail}")
            self.update_history("generate_ideas_error", {"error": "GenericException", "details": str(e), "raw_response_snippet": raw_ideas_text[:500]})

        self.update_history("generate_ideas_attempt_completed", {"prompt_length": len(prompt), "raw_response_length": len(raw_ideas_text), "parsed_ideas_count": len(generated_ideas)})

        if generated_ideas:
            print(f"{self.name} gerou e adicionou {len(generated_ideas)} novas ideias ao CompanyState.")
        else:
            print(f"{self.name}: Nenhuma ideia foi gerada ou adicionada nesta tentativa.")

        return generated_ideas
