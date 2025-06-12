import os
from typing import Any, Dict, Optional
# from dotenv import load_dotenv # Se usar .env files
# import yaml # Se usar arquivos YAML para config

# from src.core.company_settings import CompanySettings # Para popular um objeto CompanySettings

def load_app_settings(config_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Carrega configurações de variáveis de ambiente e/ou um arquivo de configuração.
    Retorna um dicionário de configurações.
    """
    # load_dotenv() # Carrega .env se existir

    settings = {}

    # Prioridade:
    # 1. Variáveis de ambiente (mais alta)
    # 2. Arquivo de configuração (se fornecido)
    # 3. Valores padrão (definidos em CompanySettings ou aqui)

    # Exemplo de carregamento de uma variável de ambiente
    settings["COMPANY_NAME"] = os.getenv("EDA_COMPANY_NAME", "Empresa Digital Padrão (via Loader)")
    settings["STARTING_BALANCE"] = float(os.getenv("EDA_STARTING_BALANCE", 10000.0))
    settings["LLM_PROVIDER"] = os.getenv("EDA_LLM_PROVIDER", "default_provider_loader")
    settings["DEFAULT_LLM_MODEL"] = os.getenv("EDA_DEFAULT_LLM_MODEL", "default_model_loader")
    settings["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    # Adicionar outras chaves de API conforme necessário

    # if config_file_path and os.path.exists(config_file_path):
    #     try:
    #         with open(config_file_path, 'r') as f:
    #             if config_file_path.endswith(".yaml") or config_file_path.endswith(".yml"):
    #                 config_from_file = yaml.safe_load(f)
    #             # elif config_file_path.endswith(".json"):
    #             #     config_from_file = json.load(f)
    #             else:
    #                 config_from_file = {} # Formato não suportado
    #
    #         # Merge, dando prioridade a env vars (que já estão em settings)
    #         for key, value in config_from_file.items():
    #             if key.upper() not in settings: # Adiciona apenas se não foi definido por env var
    #                 settings[key.upper()] = value
    #     except Exception as e:
    #         print(f"[SettingsLoader] Erro ao carregar arquivo de configuração '{config_file_path}': {e}")

    print(f"[SettingsLoader] Configurações carregadas: Provider={settings.get('LLM_PROVIDER')}")
    return settings

# Exemplo de como usar para popular CompanySettings:
# app_config_dict = load_app_settings()
# company_settings_instance = CompanySettings(
#     company_name=app_config_dict.get("COMPANY_NAME", "Fallback Name"),
#     starting_balance=app_config_dict.get("STARTING_BALANCE", 5000.0),
#     llm_provider=app_config_dict.get("LLM_PROVIDER", "default"),
#     default_llm_model=app_config_dict.get("DEFAULT_LLM_MODEL", "default")
# )
