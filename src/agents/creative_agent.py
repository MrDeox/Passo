from typing import Any, Optional
from .base_agent import BaseAgent

class CreativeAgent(BaseAgent):
    """
    Agente responsável pela ideação de novos produtos e serviços.
    """
    def __init__(self, name: str, company_state: Any, llm_integration: Any, llm_model: Optional[str] = "default_creative_model"):
        super().__init__(name, "CreativeAgent", llm_model, company_state, llm_integration)

    async def perform_task(self) -> Any:
        """
        Gera novas ideias de produtos ou serviços.
        """
        prompt = "Gerar 3 novas ideias inovadoras de produtos ou serviços digitais, considerando as tendências atuais de IA. Para cada ideia, forneça um nome, uma breve descrição e o público-alvo."

        raw_ideas_text = await self.send_prompt_to_llm(prompt)

        # Aqui, em uma implementação real, parsearíamos raw_ideas_text
        # para criar objetos Idea e adicioná-los ao company_state.
        parsed_ideas = [{"name": "Ideia Alpha", "description": "Descrição Alpha", "target_audience": "Tech"},
                        {"name": "Ideia Beta", "description": "Descrição Beta", "target_audience": "Geral"}] # Exemplo

        self.update_history("generate_ideas", {"raw_text": raw_ideas_text, "parsed_count": len(parsed_ideas)})

        # Exemplo: Adicionar ideias ao estado da empresa (a ser implementado em CompanyState)
        # for idea_data in parsed_ideas:
        #     self.company_state.add_idea(name=idea_data["name"], description=idea_data["description"],
        #                                 target_audience=idea_data["target_audience"], author=self.name)

        print(f"{self.name} gerou {len(parsed_ideas)} ideias.")
        return parsed_ideas
