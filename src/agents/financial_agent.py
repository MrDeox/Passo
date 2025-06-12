from typing import Any, Optional
from .base_agent import BaseAgent

class FinancialAgent(BaseAgent):
    """
    Agente responsável por análises financeiras, orçamentos e relatórios.
    """
    def __init__(self, name: str, company_state: Any, llm_integration: Any, llm_model: Optional[str] = "default_financial_model"):
        super().__init__(name, "FinancialAgent", llm_model, company_state, llm_integration)

    async def perform_task(self) -> Any:
        """
        Realiza uma análise financeira ou gera um relatório.
        """
        # Exemplo: Obter dados financeiros do CompanyState (a ser implementado)
        # financial_data = self.company_state.get_financial_summary()
        # Exemplo de dados financeiros simulados
        financial_data = {"revenue": 10000, "expenses": 6500, "profit": 3500, "cash_flow": 2000}

        prompt = f"Com base nos seguintes dados financeiros: Receita: {financial_data['revenue']}, Despesas: {financial_data['expenses']}, Lucro: {financial_data['profit']}, Fluxo de Caixa: {financial_data['cash_flow']}. Gere uma breve análise e sugestões para otimização de custos."

        financial_analysis_text = await self.send_prompt_to_llm(prompt)

        # Em uma implementação real, essa análise seria armazenada ou usada para tomar decisões.
        parsed_analysis = {"summary": "Análise financeira indica bom lucro...", "suggestions": ["Reduzir custos X...", "Aumentar investimento Y..."]} # Exemplo

        self.update_history("perform_financial_analysis", {"raw_text": financial_analysis_text, "parsed_analysis": parsed_analysis})

        print(f"{self.name} realizou uma análise financeira. Resumo: {parsed_analysis['summary']}")
        return parsed_analysis
