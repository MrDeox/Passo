def simulate_market_data(domain: str) -> dict:
    """Simulates market data collection for a given domain."""
    if domain == "tecnologia":
        return {
            "trending_topics": ["IA generativa", "cibersegurança", "web3", "computação quântica"],
            "competition_level": "high",
            "potential_monetization_methods": ["SaaS", "ads", "consultoria"],
        }
    elif domain == "saúde":
        return {
            "trending_topics": ["bem-estar mental", "nutrição personalizada", "telemedicina", "wearables de saúde"],
            "competition_level": "medium",
            "potential_monetization_methods": ["subscriptions", "e-commerce", "consultas online"],
        }
    elif domain == "finanças":
        return {
            "trending_topics": ["criptomoedas", "open banking", "IA em finanças", "ESG investing"],
            "competition_level": "high",
            "potential_monetization_methods": ["consultoria", "SaaS", "cursos"],
        }
    else:
        return {
            "trending_topics": ["tópico genérico 1", "tópico genérico 2", "tópico genérico 3"],
            "competition_level": "medium",
            "potential_monetization_methods": ["ads", "e-commerce"],
        }
