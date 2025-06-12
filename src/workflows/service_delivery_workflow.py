from typing import Any, Optional, Dict, List
from enum import Enum
from .base_workflow import BaseWorkflow, WorkflowStatus
# from src.core.idea import Idea, IdeaStatus # Not used directly in this skeleton
from src.core.service import ServiceStatus # Import directly
# from src.agents.execution_agent import ExecutionAgent

class ServiceDeliveryWorkflow(BaseWorkflow):
    """
    Gerencia o processo de definição de escopo, atribuição e entrega de um serviço.
    """
    def __init__(self, workflow_id: str, company_state: Any, service_id: str, settings: Optional[Dict] = None):
        super().__init__(workflow_id, company_state, settings)
        self.service_id = service_id

    async def run(self) -> bool:
        self._set_status(WorkflowStatus.RUNNING, f"Iniciando workflow de entrega de serviço ID: {self.service_id}.")

        service = self.company_state.services.get(self.service_id)
        if not service:
            self._set_status(WorkflowStatus.FAILED, f"Serviço ID {self.service_id} não encontrado.")
            return False

        self._log_step("initiation", f"Iniciando para o serviço: '{service.name}'. Status atual: {service.status.value}")

        # Passo 1: Definição de Escopo (se necessário)
        if service.status == ServiceStatus.PROPOSED:
            self._log_step("scoping_start", f"Iniciando definição de escopo para '{service.name}'.")
            service.update_status(ServiceStatus.SCOPING, {"workflow_id": self.workflow_id})
            service.scope_details = "Escopo detalhado: entrega X, Y, Z. Esforço: 20 horas. Preço: 00."
            service.estimated_effort_hours = 20
            service.price_amount = 500
            service.required_skills = ["python", "comunicação"]
            service.update_status(ServiceStatus.READY_TO_OFFER, {"workflow_id": self.workflow_id, "scope_defined": True})
            self._log_step("scoping_complete", f"Escopo para '{service.name}' definido.", {"service_id": self.service_id})

        if service.status != ServiceStatus.READY_TO_OFFER and service.status != ServiceStatus.ACTIVE_DELIVERY :
            if service.status == ServiceStatus.ACTIVE_DELIVERY:
                self._log_step("already_in_delivery", f"Serviço '{service.name}' já está em entrega. Continuando monitoramento.", level="info")
            else:
                self._set_status(WorkflowStatus.PAUSED, f"Serviço '{service.name}' não está pronto para oferta ou entrega (status: {service.status.value}). Workflow pausado.")
                return True


        # Passo 2: Aguardar Contratação / Atribuição (simulado)
        if service.status == ServiceStatus.READY_TO_OFFER:
            self._log_step("awaiting_engagement", f"Serviço '{service.name}' pronto para oferta. Aguardando 'contratação'.")
            service.update_status(ServiceStatus.ACTIVE_DELIVERY, {"workflow_id": self.workflow_id, "client_id": "client_sim_123"})
            self.company_state.log_event("SERVICE_ENGAGED", f"Serviço '{service.name}' contratado.", {"service_id": self.service_id, "client_id": "client_sim_123"})
            self._log_step("service_engaged", f"Serviço '{service.name}' foi 'contratado'. Iniciando entrega.", {"service_id": self.service_id})


        # Passo 3: Entrega do Serviço (simulado)
        if service.status == ServiceStatus.ACTIVE_DELIVERY:
            self._log_step("delivery_start", f"Iniciando entrega do serviço '{service.name}'.")
            service.completion_log.append({"timestamp": self.company_state.current_time, "event": "Marco 1 alcançado", "details": "Pesquisa inicial concluída."})
            service.completion_log.append({"timestamp": self.company_state.current_time, "event": "Marco 2 alcançado", "details": "Primeira entrega parcial feita."})

            service.update_status(ServiceStatus.COMPLETED, {"workflow_id": self.workflow_id, "delivered_by": "ExecutionAgent_Simulated"})
            self.company_state.balance += service.price_amount
            self.company_state.log_event("SERVICE_COMPLETED", f"Serviço '{service.name}' concluído. Receita: {service.price_amount}", {"service_id": self.service_id, "revenue": service.price_amount})
            self._log_step("delivery_complete", f"Entrega do serviço '{service.name}' concluída. Receita: {service.price_amount}.", {"service_id": self.service_id})

        self._set_status(WorkflowStatus.COMPLETED, f"Workflow de entrega do serviço '{service.name}' concluído.")
        return True
