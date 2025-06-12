from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum
import uuid
import time

class ProductStatus(Enum):
    CONCEPT = "CONCEITO" # Originado de uma Idea aprovada
    DEVELOPMENT = "EM DESENVOLVIMENTO"
    READY_FOR_LAUNCH = "PRONTO PARA LANÇAMENTO"
    LAUNCHED = "LANÇADO"
    DISCONTINUED = "DESCONTINUADO"

@dataclass
class Product:
    """
    Representa um produto digital ou físico desenvolvido pela empresa.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    description: str
    idea_id: Optional[str] = None # ID da ideia original
    status: ProductStatus = ProductStatus.CONCEPT
    version: str = "0.1.0"
    creation_timestamp: float = field(default_factory=time.time)
    launch_timestamp: Optional[float] = None
    development_log: List[Dict] = field(default_factory=list) # Logs de desenvolvimento
    marketing_materials_ids: List[str] = field(default_factory=list) # IDs de materiais de marketing
    sales_price: float = 0.0
    units_sold: int = 0
    total_revenue: float = 0.0

    def update_status(self, new_status: ProductStatus, details: Optional[Dict] = None):
        self.development_log.append({
            "timestamp": time.time(),
            "event": f"Status alterado de {self.status.value} para {new_status.value}",
            "details": details or {}
        })
        self.status = new_status
        if new_status == ProductStatus.LAUNCHED and not self.launch_timestamp:
            self.launch_timestamp = time.time()
