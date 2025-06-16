def simulate_market_data(domain: str) -> dict:
    """Simulates market data collection for a given domain."""
    if domain == "tecnologia":
        return {
            "trending_topics": ["IA generativa", "cibersegurança", "web3", "computação quântica", "realidade aumentada"],
            "competition_level": "high",
            "potential_monetization_methods": ["SaaS", "ads", "consultoria", "cursos premium", "licenciamento"],
            "target_audience_demographics": "tech professionals, startups, enterprises",
            "initial_investment_level": "high"
        }
    elif domain == "saúde":
        return {
            "trending_topics": ["bem-estar mental", "nutrição personalizada", "telemedicina", "wearables de saúde", "longevidade"],
            "competition_level": "medium", 
            "potential_monetization_methods": ["subscriptions", "e-commerce", "consultas online", "produtos digitais"],
            "target_audience_demographics": "young adults 18-35, parents with young children",
            "initial_investment_level": "medium"
        }
    elif domain == "finanças":
        return {
            "trending_topics": ["criptomoedas", "open banking", "IA em finanças", "ESG investing", "finanças pessoais"],
            "competition_level": "high",
            "potential_monetization_methods": ["consultoria", "SaaS", "cursos", "assinaturas", "relatórios premium"],
            "target_audience_demographics": "small business owners, investors, young professionals",
            "initial_investment_level": "medium"
        }
    else:
        return {
            "trending_topics": ["tópico genérico 1", "tópico genérico 2", "tópico genérico 3"],
            "competition_level": "medium",
            "potential_monetization_methods": ["ads", "e-commerce"],
            "target_audience_demographics": "general audience",
            "initial_investment_level": "low"
        }
