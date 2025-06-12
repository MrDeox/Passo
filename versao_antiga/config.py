import os

# From ciclo_criativo.py
PRODUTOS_MARKETING_DIR = "produtos_marketing"

# From criador_de_produtos.py
PRODUTOS_GERADOS_DIR = "produtos_gerados"

# From empresa_digital.py
MODO_VIDA_INFINITA: bool = os.environ.get("MODO_VIDA_INFINITA", "0") == "1"
HOURS_PER_CYCLE_FACTOR: float = 8.0
HOURS_PER_CYCLE_FACTOR_VIDA_INFINITA: float = 16.0
OPENROUTER_CALL_DELAY_SECONDS: float = 1.0
MAX_LLM_AGENTS_PER_CYCLE: int = 5

# Added constant
NOME_EMPRESA: str = "Empresa Digital"
