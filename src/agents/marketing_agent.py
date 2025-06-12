from typing import Any, Optional
from .base_agent import BaseAgent

class MarketingAgent(BaseAgent):
    """
    Agente responsável pela criação de estratégias de marketing e conteúdo de divulgação.
    """
    def __init__(self, name: str, company_state: Any, llm_integration: Any, llm_model: Optional[str] = "default_marketing_model"):
        super().__init__(name, "MarketingAgent", llm_model, company_state, llm_integration)

    async def perform_task(self) -> Any:
        """
        Cria conteúdo de marketing para um produto/serviço lançado.
        """
        # Exemplo: Obter um produto/serviço lançado para marketing (a ser implementado)
        # item_to_market = self.company_state.get_launched_item_for_marketing()
        item_to_market = {"type": "Product", "name": "Ideia Alpha Deluxe", "description": "Versão finalizada da Ideia Alpha"} # Exemplo

        if not item_to_market:
            print(f"{self.name} não encontrou itens para marketing.")
            self.update_history("generate_marketing_content", {"status": "no_item_to_market"})
            return None

        prompt = f"Crie um post de blog e 3 tweets para divulgar o seguinte {item_to_market['type']}: Nome: {item_to_market['name']}, Descrição: {item_to_market['description']}."

        marketing_content_text = await self.send_prompt_to_llm(prompt)

        # Em uma implementação real, o conteúdo seria armazenado e possivelmente enviado para plataformas.
        parsed_content = {"blog_post": "Título do Blog...", "tweets": ["Tweet 1...", "Tweet 2...", "Tweet 3..."]} # Exemplo

        self.update_history("generate_marketing_content", {"item_name": item_to_market['name'], "raw_text": marketing_content_text, "parsed_content": parsed_content})

        # Exemplo: Adicionar conteúdo ao CompanyState ou a um repositório de marketing
        # self.company_state.add_marketing_material(item_name=item_to_market['name'], content=parsed_content)

        print(f"{self.name} gerou conteúdo de marketing para '{item_to_market['name']}'.")
        return parsed_content
