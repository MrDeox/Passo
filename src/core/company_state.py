from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import time

from .company_settings import CompanySettings
from .idea import Idea
from .product import Product
from .service import Service
from .task import Task, TaskStatus
from .event import Event
# from src.agents.base_agent import BaseAgent # Para type hinting, evitar import circular

@dataclass
class CompanyState:
    """
    Mantém o estado global da empresa e da simulação.
    """
    settings: CompanySettings = field(default_factory=CompanySettings)
    current_cycle: int = 0
    current_time: float = field(default_factory=time.time) # Tempo simulado ou real

    balance: float = 0.0 # Saldo financeiro

    ideas: Dict[str, Idea] = field(default_factory=dict)
    products: Dict[str, Product] = field(default_factory=dict)
    services: Dict[str, Service] = field(default_factory=dict)
    tasks: Dict[str, Task] = field(default_factory=dict)

    # agents: Dict[str, 'BaseAgent'] = field(default_factory=dict) # Será populado pelo módulo de agentes

    event_log: List[Event] = field(default_factory=list)

    # Métricas e KPIs
    metrics: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        self.balance = self.settings.starting_balance
        self.log_event("COMPANY_STATE_INITIALIZED", "Estado da empresa inicializado.", {"settings": str(self.settings)})

    def advance_cycle(self):
        self.current_cycle += 1
        self.current_time = time.time() # Ou lógica de tempo simulado
        self.log_event("CYCLE_ADVANCED", f"Ciclo avançado para {self.current_cycle}.")
        # Aqui podem entrar lógicas de atualização de estado por ciclo (ex: custos fixos)

    def log_event(self, event_type: str, description: str, payload: Optional[Dict] = None, source: Optional[str] = None):
        event = Event(
            event_type=event_type,
            description=description,
            payload=payload or {},
            source=source or "CompanyState"
        )
        self.event_log.append(event)
        # print(f"[EVENT:{event_type}] {description}") # Opcional: logar no console

    # --- Métodos para gerenciar Ideias ---
    def add_idea(self, idea: Idea):
        if idea.id not in self.ideas:
            self.ideas[idea.id] = idea
            self.log_event("IDEA_CREATED", f"Ideia '{idea.name}' criada.", {"idea_id": idea.id, "author": idea.author_agent_name})
        else:
            self.log_event("IDEA_ADD_FAILED", f"Tentativa de adicionar ideia já existente: {idea.id}", {"idea_id": idea.id}, "CompanyState.add_idea")

    def get_idea(self, idea_id: str) -> Optional[Idea]:
        return self.ideas.get(idea_id)

    # --- Métodos para gerenciar Produtos ---
    def add_product(self, product: Product):
        if product.id not in self.products:
            self.products[product.id] = product
            self.log_event("PRODUCT_ADDED", f"Produto '{product.name}' adicionado.", {"product_id": product.id, "idea_id": product.idea_id})

    # --- Métodos para gerenciar Serviços ---
    def add_service(self, service: Service):
        if service.id not in self.services:
            self.services[service.id] = service
            self.log_event("SERVICE_ADDED", f"Serviço '{service.name}' adicionado.", {"service_id": service.id, "idea_id": service.idea_id})

    # --- Métodos para gerenciar Tarefas ---
    def add_task(self, task: Task):
        if task.id not in self.tasks:
            self.tasks[task.id] = task
            self.log_event("TASK_CREATED", f"Tarefa '{task.name}' criada.", {"task_id": task.id, "status": task.status.value})
        else:
            self.log_event("TASK_ADD_FAILED", f"Tentativa de adicionar tarefa já existente: {task.id}", {"task_id": task.id})

    def get_pending_tasks_for_role(self, role: str) -> List[Task]:
        return [t for t in self.tasks.values() if t.status == TaskStatus.PENDING and t.assigned_to_role == role]

    def get_task(self, task_id: str) -> Optional[Task]:
        return self.tasks.get(task_id)

    # Outros métodos de conveniência (ex: para encontrar itens por status, etc.) podem ser adicionados.
