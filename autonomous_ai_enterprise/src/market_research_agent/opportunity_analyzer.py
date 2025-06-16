def analyze_and_suggest_opportunity(market_data: dict) -> dict:
    """Analyzes market data and suggests a business opportunity with monetization strategy.
    
    Args:
        market_data: Dictionary containing simulated market data
        
    Returns:
        Dictionary with suggested opportunity details including:
        - opportunity_name
        - description
        - suggested_format
        - monetization_strategy
        - target_audience
        - estimated_effort
    """
    # Extract relevant data from input
    trending_topics = market_data.get('trending_topics', [])
    competition = market_data.get('competition_level', 'medium')
    monetization_methods = market_data.get('potential_monetization_methods', [])
    audience = market_data.get('target_audience_demographics', 'general audience')
    investment_level = market_data.get('initial_investment_level', 'medium')

    # Determine opportunity type based on competition and trends
    if competition in ['low', 'medium'] and trending_topics:
        if competition == 'low':
            opportunity_type = "primeiro a entrar"
            format_options = ["Plataforma", "Serviço", "Produto"]
        else:
            opportunity_type = "nicho especializado"
            format_options = ["Conteúdo Especializado", "Serviço Premium", "Produto Diferenciado"]
        
        # Select format based on investment level
        if investment_level == 'high':
            suggested_format = format_options[0]  # Plataforma/Conteúdo Especializado
        elif investment_level == 'medium':
            suggested_format = format_options[1]  # Serviço/Serviço Premium
        else:
            suggested_format = format_options[2]  # Produto/Produto Diferenciado
        
        # Build opportunity details
        main_topic = trending_topics[0]
        opportunity_name = f"{suggested_format} de {main_topic} para {audience.split(',')[0].strip()}"
        description = f"Oportunidade de {opportunity_type} no mercado de {main_topic} com foco em {audience}."
        
    else:
        # Default suggestion for high competition or no trends
        opportunity_name = f"Serviço Genérico para {audience}"
        description = "Oportunidade genérica considerando o alto nível de competição no mercado."
        suggested_format = "Serviço Básico"

    # Determine monetization strategy
    if monetization_methods:
        if len(monetization_methods) > 1:
            monetization_strategy = f"{monetization_methods[0]} e {monetization_methods[1]}"
        else:
            monetization_strategy = monetization_methods[0]
    else:
        monetization_strategy = "Modelo a ser definido"

    # Estimate effort based on investment level and opportunity complexity
    if investment_level == 'high' or competition == 'high':
        estimated_effort = "Alto"
    elif investment_level == 'medium' and competition == 'medium':
        estimated_effort = "Médio"
    else:
        estimated_effort = "Baixo"

    return {
        "opportunity_name": opportunity_name,
        "description": description,
        "suggested_format": suggested_format,
        "monetization_strategy": monetization_strategy,
        "target_audience": audience,
        "estimated_effort": estimated_effort
    }
