from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
import uuid
import time

class IdeaStatus(Enum):
    PROPOSED = "PROPOSTA"
    VALIDATING = "EM VALIDAÇÃO"
    VALIDATED_APPROVED = "VALIDADA (APROVADA)"
    VALIDATED_REJECTED = "VALIDADA (REJEITADA)"
    ARCHIVED = "ARQUIVADA"

@dataclass
class Idea:
    """
    Representa uma ideia de produto ou serviço.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    author_agent_name: Optional[str] = None
    target_audience: Optional[str] = None
    creation_timestamp: float = field(default_factory=time.time)
    status: IdeaStatus = IdeaStatus.PROPOSED
    validation_details: Optional[Dict] = field(default_factory=dict) # ex: {"validator_agent": "nome", "score": 8, "comments": "..."}
    linked_product_id: Optional[str] = None
    linked_service_id: Optional[str] = None
    history: List[Dict] = field(default_factory=list) # Log de mudanças de status, etc.

    def update_status(self, new_status: IdeaStatus, details: Optional[Dict] = None):
        self.history.append({
            "timestamp": time.time(),
            "old_status": self.status.value,
            "new_status": new_status.value,
            "details": details or {}
        })
        self.status = new_status
        if details:
            self.history[-1]["details"].update(details)
