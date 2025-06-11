from dataclasses import dataclass, field
from typing import Optional, List, Dict
import re # For slug generation
import uuid # For Task and Service IDs
import time # For Task and Service history timestamps

# Helper function for slug generation (can be outside or static method if preferred)
def _generate_slug(text: str) -> str:
    if not text:
        return "untitled-idea"
    # Remove accents and special characters (keeping alphanumeric, spaces, hyphens)
    s = re.sub(r'[^\w\s-]', '', text.lower())
    # Replace whitespace and multiple hyphens with a single hyphen
    s = re.sub(r'[-\s]+', '-', s).strip('-')
    if not s: # If all characters were special and removed
        return "untitled-idea-" + uuid.uuid4().hex[:6]
    return s[:50] # Limit length

@dataclass
class Ideia:
    descricao: str
    justificativa: str
    autor: str # Nome do agente que propôs a ideia
    validada: bool = False
    executada: bool = False # Se a prototipagem/execução já ocorreu
    resultado: float = 0.0  # Resultado financeiro da ideia após execução/prototipagem
    link_produto: Optional[str] = None # Link para o produto na Gumroad, se criado

    # Adicionar outros campos relevantes que possam ter sido adicionados em Ideia
    # Por exemplo, se complexidade, potencial_lucro, prioridade foram adicionados antes
    # complexidade: int = 1
    # potencial_lucro: int = 1
    # prioridade: int = 1
    # No estado atual do código, esses campos extras não existem na definição principal de Ideia.

    # Se Ideia precisar de métodos ou ser mais complexa, pode evoluir aqui.
    # Por agora, é uma simples dataclass para transferência de dados.

    @property
    def slug(self) -> str:
        return _generate_slug(self.descricao)

# Poderíamos também mover outras dataclasses compartilhadas aqui no futuro,
# como definições base para Agente ou Local, se isso ajudar a quebrar outras dependências,
# mas por agora, apenas Ideia é o foco para resolver a dependência circular imediata.

# O histórico_ideias e preferencia_temas permanecem em ciclo_criativo.py por enquanto,
# pois são estados globais daquele módulo. As funções de salvar/carregar
# também permanecem lá, operando nesse estado global.
# empresa_digital.py chama essas funções, o que é uma dependência aceitável.
# O problema principal era a dependência de tipo (Ideia) entre os módulos.

# uuid and time imports are already present due to Service and Task dataclasses.

@dataclass
class Service:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    service_name: str
    description: str
    author: str  # Nome do agente que propôs
    required_skills: List[str] = field(default_factory=list) # e.g., ["Consultant", "Developer"]
    estimated_effort_hours: int = 0
    pricing_model: str = "fixed_price" # e.g., "fixed_price", "hourly_rate"
    price_amount: float = 0.0
    status: str = "proposed" # e.g., "proposed", "validated", "rejected", "in_progress", "completed", "cancelled"
    history: List[Dict[str, str]] = field(default_factory=list) # Log status changes
    creation_timestamp: float = field(default_factory=time.time)
    validation_timestamp: Optional[float] = None
    completion_timestamp: Optional[float] = None
    assigned_agent_name: Optional[str] = None
    delivery_start_timestamp: Optional[float] = None
    revenue_calculated: bool = False # New field
    cycles_unassigned: int = 0 # New field for tracking validated but unassigned cycles
    progress_hours: float = 0.0 # New field for tracking progress on service execution


    def __post_init__(self):
        # Ensure history is initialized only if it's empty (e.g., on new creation)
        # This check might be redundant if default_factory always creates a new list,
        # but it's safer if the object is ever manually instantiated with history=None.
        if not self.history and self.status == "proposed": # Only add "proposed" if truly new
            self.history.append({"timestamp": str(self.creation_timestamp), "status": self.status, "message": "Service proposed"})

    def update_status(self, new_status: str, message: str = ""):
        old_status = self.status
        self.status = new_status
        timestamp = time.time()

        log_entry_message = message or f"Status changed from {old_status} to {new_status}"

        if new_status == "validated" and old_status == "proposed":
            self.validation_timestamp = timestamp
        elif new_status == "in_progress" and old_status == "validated":
            # delivery_start_timestamp should ideally be set when assigned,
            # but update_status can log the transition to in_progress.
            # Actual setting of delivery_start_timestamp will be handled by assignment logic.
            pass # No specific timestamp here, just status change
        elif new_status == "completed" or new_status == "cancelled":
            if self.status != old_status: # only set timestamp if it's a new completion/cancellation
                 self.completion_timestamp = timestamp

        log_entry = {"timestamp": str(timestamp), "status": new_status}
        if log_entry_message: # Use the more descriptive message
            log_entry["message"] = log_entry_message
        self.history.append(log_entry)

    def assign_agent(self, agent_name: str, message: str = ""):
        if self.status == "validated":
            self.assigned_agent_name = agent_name
            self.delivery_start_timestamp = time.time()
            self.progress_hours = 0.0 # Reset progress upon assignment/re-assignment
            self.cycles_unassigned = 0 # Reset unassigned counter
            log_message = message or f"Assigned to agent {agent_name}"
            self.update_status("in_progress", log_message)
        else:
            # Potentially raise an error or log a warning if trying to assign a non-validated service
            # Using print for now, should ideally be logger for consistency
            print(f"Warning: Tried to assign agent to service {self.id} (status: {self.status}). Expected 'validated'.")

    def complete_service(self, message: str = ""):
        if self.status == "in_progress":
            log_message = message or "Service marked as completed"
            # self.completion_timestamp is set by update_status
            # self.revenue_calculated should be False by default, will be set to True by billing logic
            self.update_status("completed", log_message)
        else:
            # Potentially raise an error or log a warning
            print(f"Warning: Tried to complete service {self.id} (status: {self.status}). Expected 'in_progress'.")

# Need to ensure time is imported if not already, for Task.update_status
# import time # Already imported at the top level of the original core_types.py

@dataclass
class Task:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    description: str
    status: str = "todo"  # "todo", "in_progress", "done"
    history: List[Dict[str, str]] = field(default_factory=list) # To log status changes or agent assignments

    def update_status(self, new_status: str, message: str = ""):
        # time is imported at the top level of this file
        valid_statuses = ["todo", "in_progress", "done"]
        if new_status not in valid_statuses:
            # In a real app, might use logging.error or raise ValueError
            print(f"Error: Attempted to set invalid status '{new_status}' for task '{self.id}'. Valid statuses are: {valid_statuses}")
            return

        old_status = self.status
        self.status = new_status
        timestamp = time.time() # Using numeric timestamp for consistency with Service

        log_entry = {
            "timestamp": str(timestamp),
            "status": new_status,
            "message": message or f"Status changed from {old_status} to {new_status}"
        }
        self.history.append(log_entry)
        # Consider global event logging if needed:
        # import empresa_digital as ed # Would create circular import if done at top level
        # ed.registrar_evento(f"Task '{self.description[:30]}...' (ID: {self.id}) status updated to {new_status}. Message: {message}")
        # For now, history on the object is primary. Global logging can be done by the caller.
