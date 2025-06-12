from dataclasses import dataclass, field
from typing import Any, Dict
import time
import uuid

@dataclass
class Event:
    """
    Registra um evento significativo que ocorreu na simulação/empresa.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    event_type: str # Ex: "IDEA_CREATED", "PRODUCT_LAUNCHED", "AGENT_ACTION", "FINANCIAL_TRANSACTION"
    description: str # Descrição textual do evento
    payload: Dict[str, Any] = field(default_factory=dict) # Dados adicionais relevantes ao evento
    source: Optional[str] = None # Nome do agente, módulo ou sistema que originou o evento
