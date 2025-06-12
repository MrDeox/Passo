from dataclasses import dataclass, field
from typing import List

@dataclass
class CompanySettings:
    """
    Configurações da empresa e da simulação.
    """
    company_name: str = "Empresa Digital Autônoma (EDA)"
    starting_balance: float = 10000.0
    max_simulation_cycles: int = 100 # 0 para infinito
    llm_provider: str = "default_provider" # Ex: 'openai', 'openrouter', 'google_vertex'
    default_llm_model: str = "default_model"
    # Outras configurações relevantes podem ser adicionadas aqui
    # Ex: custos operacionais, taxas de juros, etc.
