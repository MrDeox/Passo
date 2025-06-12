from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
import uuid
import time

class ServiceStatus(Enum):
    PROPOSED = "PROPOSTO" # Originado de uma Idea aprovada ou proposta direta
    SCOPING = "EM DEFINIÇÃO DE ESCOPO"
    READY_TO_OFFER = "PRONTO PARA OFERECER"
    ACTIVE_DELIVERY = "EM ENTREGA" # Cliente contratou
    COMPLETED = "CONCLUÍDO"
    CANCELLED = "CANCELADO"

@dataclass
class Service:
    """
    Representa um serviço oferecido pela empresa.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    idea_id: Optional[str] = None # ID da ideia original, se aplicável
    status: ServiceStatus = ServiceStatus.PROPOSED
    creation_timestamp: float = field(default_factory=time.time)

    scope_details: Optional[str] = None
    required_skills: List[str] = field(default_factory=list)
    estimated_effort_hours: float = 0.0
    pricing_model: str = "fixed_price" # ou "hourly_rate", "subscription"
    price_amount: float = 0.0

    active_engagements: List[Dict] = field(default_factory=list) # Detalhes de clientes/projetos ativos
    completion_log: List[Dict] = field(default_factory=list) # Logs de entrega e conclusão

    def update_status(self, new_status: ServiceStatus, details: Optional[Dict] = None):
        self.completion_log.append({
            "timestamp": time.time(),
            "event": f"Status alterado de {self.status.value} para {new_status.value}",
            "details": details or {}
        })
        self.status = new_status
