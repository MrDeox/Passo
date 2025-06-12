# Valores Padrão de Configuração
# Estes valores podem ser sobrescritos por src.utils.settings_loader
# que por sua vez pode carregar de variáveis de ambiente ou arquivos de configuração.

# --- Configurações Gerais da Empresa/Simulação ---
COMPANY_NAME: str = "EDA (Empresa Digital Autônoma) - Padrão Config"
STARTING_BALANCE: float = 5000.0
MAX_SIMULATION_CYCLES: int = 0 # 0 para infinito, >0 para número fixo de ciclos

# --- Configurações de LLM ---
# Provider pode ser "openai", "openrouter", "google_vertex", "mock", etc.
LLM_PROVIDER: str = "mock" # Usar "mock" para não fazer chamadas reais inicialmente
DEFAULT_LLM_MODEL: str = "mock_model_v1"

# Chaves de API (idealmente carregadas de env vars ou um arquivo .env via settings_loader)
# Estes são placeholders e não devem ser commitados com valores reais.
OPENAI_API_KEY: str = "sk-your_openai_api_key_here_if_not_using_env"
OPENROUTER_API_KEY: str = "your_openrouter_api_key_here_if_not_using_env"
# Adicionar outras chaves conforme necessário

# --- Configurações de Logging ---
LOG_LEVEL: str = "INFO" # "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"
LOG_FILE: str = "eda_simulation.log"

# --- Outras Configurações ---
# Ex: Caminhos de arquivos, URLs de serviços externos, etc.
DATA_SAVE_PATH: str = "./data_eda/" # Onde salvar estados, logs, etc.

# print(f"[Config] Módulo de configuração carregado. Provider LLM padrão: {LLM_PROVIDER}") # Comentado

# Em uma aplicação mais complexa, poderia usar Pydantic aqui:
# from pydantic_settings import BaseSettings
# class AppSettings(BaseSettings):
#     COMPANY_NAME: str = "EDA Pydantic"
#     STARTING_BALANCE: float = 1000.0
#     LLM_PROVIDER: str = "pydantic_mock"
#     # ... outras configs com tipos e validações
#     class Config:
#         env_file = ".env" # Exemplo de carregar de .env
#         env_prefix = "EDA_" # Ex: EDA_COMPANY_NAME
# settings = AppSettings()
# print(f"[Config] Pydantic settings carregadas: {settings.COMPANY_NAME}")
