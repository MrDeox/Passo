import uuid
import time
from typing import Optional

def generate_unique_id(prefix: Optional[str] = None) -> str:
    """
    Gera um ID único, opcionalmente com um prefixo.
    """
    id_val = str(uuid.uuid4())
    if prefix:
        return f"{prefix}_{id_val}"
    return id_val

def get_current_timestamp_ms() -> int:
    """
    Retorna o timestamp atual em milissegundos.
    """
    return int(time.time() * 1000)

def format_currency(amount: float, currency_symbol: str = "R$") -> str:
    """
    Formata um valor float como moeda.
    """
    return f"{currency_symbol} {amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# Adicionar outras funções utilitárias conforme necessário.
# print("[Helpers] Funções utilitárias básicas definidas.") # Comentado para não poluir output do script
