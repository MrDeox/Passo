from dataclasses import dataclass, field
from typing import Optional, Any, List, Dict
from enum import Enum
import uuid
import time

class TaskStatus(Enum):
    PENDING = "PENDENTE"
    ASSIGNED = "ATRIBUÍDA"
    IN_PROGRESS = "EM PROGRESSO"
    COMPLETED = "CONCLUÍDA"
    FAILED = "FALHOU"
    CANCELLED = "CANCELADA"

@dataclass
class Task:
    """
    Representa uma tarefa a ser executada por um agente ou workflow.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str # Um nome curto para a tarefa
    description: str # Descrição mais detalhada
    status: TaskStatus = TaskStatus.PENDING
    priority: int = 5 # 1 (mais alta) - 10 (mais baixa)

    created_by_agent_name: Optional[str] = None # Agente que criou/solicitou
    assigned_to_agent_name: Optional[str] = None # Agente atualmente responsável
    assigned_to_role: Optional[str] = None # Papel do agente que deveria pegar (ex: CreativeAgent)

    creation_timestamp: float = field(default_factory=time.time)
    assignment_timestamp: Optional[float] = None
    completion_timestamp: Optional[float] = None

    related_item_id: Optional[str] = None # ID de uma Idea, Product, Service, etc.
    related_item_type: Optional[str] = None # "Idea", "Product", "Service"

    dependencies: List[str] = field(default_factory=list) # Lista de IDs de tarefas que devem ser concluídas antes
    sub_tasks_ids: List[str] = field(default_factory=list) # Tarefas filhas

    result: Optional[Any] = None # Resultado da tarefa quando concluída
    history: List[Dict] = field(default_factory=list) # Histórico de mudanças de status, atribuições, etc.

    def update_status(self, new_status: TaskStatus, details: Optional[Dict] = None, agent_name: Optional[str] = None):
        log_entry = {
            "timestamp": time.time(),
            "old_status": self.status.value,
            "new_status": new_status.value,
            "details": details or {}
        }
        if agent_name:
            log_entry["agent_name"] = agent_name

        self.history.append(log_entry)
        self.status = new_status

        if new_status == TaskStatus.ASSIGNED and not self.assignment_timestamp:
            self.assignment_timestamp = time.time()
        elif new_status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED] and not self.completion_timestamp:
            self.completion_timestamp = time.time()
