from src.utils.data_simulator import simulate_market_data
from config.settings import DEFAULT_DOMAIN

def run_market_research_agent():
    """Runs the market research agent."""
    print(f"Iniciando pesquisa de mercado para o domínio: {DEFAULT_DOMAIN}")
    print("-" * 30)

    market_data = simulate_market_data(DEFAULT_DOMAIN)

    print("\nDados de Mercado Simulados:")
    print(f"  Tópicos em Alta: {', '.join(market_data['trending_topics'])}")
    print(f"  Nível de Competição: {market_data['competition_level']}")
    print(f"  Métodos de Monetização Potenciais: {', '.join(market_data['potential_monetization_methods'])}")
    print("-" * 30)

    # Simulação de identificação de oportunidade
    suggested_opportunity = "N/A"
    basic_monetization_plan = "N/A"

    if market_data["competition_level"] in ["low", "medium"] and market_data["trending_topics"]:
        suggested_opportunity = f"Desenvolver uma solução inovadora em '{market_data['trending_topics'][0]}' para o mercado de {DEFAULT_DOMAIN}."
        if market_data["potential_monetization_methods"]:
            basic_monetization_plan = f"Iniciar com foco em {market_data['potential_monetization_methods'][0]} e explorar {market_data['potential_monetization_methods'][1]}."
        else:
            basic_monetization_plan = "Definir estratégia de monetização conforme o desenvolvimento."
    elif market_data["trending_topics"]:
        suggested_opportunity = f"Explorar nichos dentro de '{market_data['trending_topics'][0]}' no mercado de {DEFAULT_DOMAIN} para diferenciar da alta competição."
        if market_data["potential_monetization_methods"]:
            basic_monetization_plan = f"Focar em um modelo de {market_data['potential_monetization_methods'][0]} altamente especializado."
        else:
            basic_monetization_plan = "Definir estratégia de monetização conforme o desenvolvimento."
    else:
        suggested_opportunity = "Nenhum tópico em alta identificado para gerar uma sugestão clara."
        basic_monetization_plan = "Reavaliar o mercado ou expandir a coleta de dados."


    print("\nSugestão do Agente:")
    print(f"  Oportunidade de Negócio Sugerida: {suggested_opportunity}")
    print(f"  Plano de Monetização Básico: {basic_monetization_plan}")
    print("-" * 30)

if __name__ == "__main__":
    run_market_research_agent()
