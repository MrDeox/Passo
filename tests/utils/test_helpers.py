import pytest
from src.utils.helpers import generate_unique_id, get_current_timestamp_ms, format_currency
import time # Necessário para o teste de timestamp

def test_generate_unique_id_no_prefix():
    """Testa a geração de ID único sem prefixo."""
    uid1 = generate_unique_id()
    uid2 = generate_unique_id()
    assert isinstance(uid1, str)
    assert len(uid1) == 36 # UUID4
    assert uid1 != uid2

def test_generate_unique_id_with_prefix():
    """Testa a geração de ID único com prefixo."""
    prefix = "task"
    uid = generate_unique_id(prefix=prefix)
    assert uid.startswith(f"{prefix}_")
    assert len(uid) == len(prefix) + 1 + 36

def test_get_current_timestamp_ms():
    """Testa se o timestamp em ms é um int e parece razoável."""
    ts_ms = get_current_timestamp_ms()
    assert isinstance(ts_ms, int)
    # Verifica se está aproximadamente correto (em relação a time.time())
    assert abs(ts_ms / 1000 - time.time()) < 1 # Deve estar dentro de 1 segundo

def test_format_currency_default_symbol():
    """Testa a formatação de moeda com símbolo padrão (R$)."""
    assert format_currency(1234.56) == "R$ 1.234,56"
    assert format_currency(0.5) == "R$ 0,50"
    assert format_currency(1000000) == "R$ 1.000.000,00"
    assert format_currency(789.1) == "R$ 789,10"

def test_format_currency_custom_symbol():
    """Testa a formatação de moeda com símbolo customizado."""
    assert format_currency(1234.56, currency_symbol="USD") == "USD 1.234,56"
    assert format_currency(50.99, currency_symbol="€") == "€ 50,99"
