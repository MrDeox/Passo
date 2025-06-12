from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List # Added List
from enum import Enum # Added Enum

# from src.core.company_state import CompanyState
# from src.agents.base_agent import BaseAgent # Para type hinting

class WorkflowStatus(str, Enum): # Using str and Enum for easy serialization if needed
    PENDING = "PENDENTE"
    RUNNING = "EM EXECUÇÃO"
    COMPLETED = "CONCLUÍDO"
    FAILED = "FALHOU"
    PAUSED = "PAUSADO"

class BaseWorkflow(ABC):
    """
    Classe base abstrata para todos os workflows.
    Um workflow gerencia um processo de negócio específico, coordenando agentes e atualizando o estado da empresa.
    """
    def __init__(self, workflow_id: str, company_state: Any, settings: Optional[Dict] = None):
        self.workflow_id = workflow_id
        self.company_state = company_state # Referência ao estado global da empresa
        self.status = WorkflowStatus.PENDING
        self.history: List[Dict[str, Any]] = []
        self.settings = settings or {} # Configurações específicas do workflow
        self.current_step: Optional[str] = None

    @abstractmethod
    async def run(self) -> bool:
        """
        Método principal para executar o workflow.
        Retorna True se o workflow foi concluído com sucesso, False caso contrário.
        Deve ser implementado por cada subclasse.
        """
        pass

    def _set_status(self, new_status: WorkflowStatus, message: Optional[str] = None):
        timestamp = self.company_state.current_time # Assumindo que company_state tem current_time
        self.history.append({
            "timestamp": timestamp,
            "old_status": self.status.value,
            "new_status": new_status.value,
            "step": self.current_step,
            "message": message or f"Status alterado para {new_status.value}"
        })
        self.status = new_status
        self.company_state.log_event(
            event_type=f"WORKFLOW_{self.__class__.__name__.upper()}_{new_status.value}",
            description=message or f"Workflow {self.workflow_id} ({self.__class__.__name__}) mudou para {new_status.value}",
            payload={"workflow_id": self.workflow_id, "step": self.current_step},
            source=self.__class__.__name__
        )
        print(f"Workflow {self.workflow_id} ({self.__class__.__name__}): Status alterado para {new_status.value}. Step: {self.current_step}. Mensagem: {message}")

    def _log_step(self, step_name: str, message: str, payload: Optional[Dict] = None, level: str = "info"): # Added level
        self.current_step = step_name
        timestamp = self.company_state.current_time
        log_entry = {
            "timestamp": timestamp,
            "step": step_name,
            "message": message,
            "level": level, # Added level
            "payload": payload or {}
        }
        self.history.append(log_entry)
        self.company_state.log_event(
            event_type=f"WORKFLOW_{self.__class__.__name__.upper()}_STEP",
            description=f"Workflow {self.workflow_id} ({self.__class__.__name__}) executou passo '{step_name}': {message}",
            payload={"workflow_id": self.workflow_id, "step": step_name, "level": level, **(payload or {})}, # Added level
            source=self.__class__.__name__
        )
        print(f"Workflow {self.workflow_id} ({self.__class__.__name__}) - Step '{step_name}' [{level.upper()}]: {message}")


    async def _assign_task_to_agent_role(self, task_name: str, task_description: str, role: str, related_item_id: Optional[str] = None, related_item_type: Optional[str] = None) -> Optional[Any]: # Task object
        """
        Cria uma tarefa e a marca para um papel de agente específico.
        Retorna o objeto Task criado ou None se falhar.
        """
        from src.core.task import Task # Import local para evitar problemas de importação circular no nível do módulo

        new_task = Task(
            name=task_name,
            description=task_description,
            assigned_to_role=role,
            created_by_agent_name="Workflow:" + self.__class__.__name__,
            related_item_id=related_item_id,
            related_item_type=related_item_type
        )
        self.company_state.add_task(new_task)
        self._log_step("assign_task", f"Tarefa '{task_name}' criada e pendente para o papel '{role}'.", {"task_id": new_task.id})

        # Em um sistema real, haveria um mecanismo para notificar agentes daquele papel
        # ou para um agente daquele papel pegar a tarefa.
        # Por enquanto, o workflow apenas cria a tarefa.
        return new_task

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id='{self.workflow_id}', status='{self.status.value}')"
