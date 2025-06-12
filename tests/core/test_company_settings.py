import pytest
from src.core.company_settings import CompanySettings

def test_company_settings_defaults():
    """Testa os valores padrão de CompanySettings."""
    settings = CompanySettings()
    assert settings.company_name == "Empresa Digital Autônoma (EDA)"
    assert settings.starting_balance == 10000.0
    assert settings.max_simulation_cycles == 100
    assert settings.llm_provider == "default_provider"
    assert settings.default_llm_model == "default_model"

def test_company_settings_custom_values():
    """Testa a atribuição de valores customizados."""
    custom_name = "Minha Super Empresa"
    custom_balance = 25000.0
    settings = CompanySettings(company_name=custom_name, starting_balance=custom_balance)
    assert settings.company_name == custom_name
    assert settings.starting_balance == custom_balance
    # Verifica se os outros defaults permanecem
    assert settings.max_simulation_cycles == 100
