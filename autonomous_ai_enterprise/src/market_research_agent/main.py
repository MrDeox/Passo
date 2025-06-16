from src.utils.data_simulator import simulate_market_data
from config.settings import DEFAULT_DOMAIN
from .opportunity_analyzer import analyze_and_suggest_opportunity

def run_market_research_agent():
    """Runs the market research agent with enhanced analysis."""
    print(f"Iniciando pesquisa de mercado para o domínio: {DEFAULT_DOMAIN}")
    print("-" * 50)

    # Simulate market data
    market_data = simulate_market_data(DEFAULT_DOMAIN)

    # Print raw simulated data
    print("\nDados de Mercado Simulados:")
    print(f"  Tópicos em Alta: {', '.join(market_data['trending_topics'])}")
    print(f"  Nível de Competição: {market_data['competition_level']}")
    print(f"  Métodos de Monetização Potenciais: {', '.join(market_data['potential_monetization_methods'])}")
    print(f"  Público-Alvo: {market_data['target_audience_demographics']}")
    print(f"  Nível de Investimento Inicial: {market_data['initial_investment_level']}")
    print("-" * 50)

    # Analyze and suggest opportunity
    opportunity = analyze_and_suggest_opportunity(market_data)

    # Print formatted opportunity suggestion
    print("\nAnálise de Oportunidade Detalhada:")
    print(f"  Nome: {opportunity['opportunity_name']}")
    print(f"  Descrição: {opportunity['description']}")
    print(f"  Formato Sugerido: {opportunity['suggested_format']}")
    print(f"  Estratégia de Monetização: {opportunity['monetization_strategy']}")
    print(f"  Público-Alvo: {opportunity['target_audience']}")
    print(f"  Esforço Estimado: {opportunity['estimated_effort']}")
    print("-" * 50)

if __name__ == "__main__":
    run_market_research_agent()
