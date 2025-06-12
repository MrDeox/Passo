from typing import Optional, Dict, List, Any
# from src.core.company_state import CompanyState
# from src.core.idea import Idea, IdeaStatus
# from src.core.service import Service, ServiceStatus

class ServiceManager:
    """
    Gerencia a lógica de criação, definição de escopo e ciclo de vida de serviços.
    """
    def __init__(self, company_state: Any):
        self.company_state = company_state

    def define_service_from_idea(self, idea_id: str, initial_name: Optional[str] = None, initial_description: Optional[str] = None) -> Optional[Any]: # Service
        """
        Define um novo Service com base em uma Idea aprovada.
        """
        idea = self.company_state.get_idea(idea_id)

        from src.core.idea import IdeaStatus # Import local
        from src.core.service import Service, ServiceStatus # Import local

        if not idea:
            print(f"[ServiceManager] Ideia ID {idea_id} não encontrada.")
            return None

        if idea.status != IdeaStatus.VALIDATED_APPROVED:
            print(f"[ServiceManager] Ideia '{idea.name}' (ID: {idea_id}) não está aprovada para desenvolvimento de serviço.")
            return None

        if idea.linked_service_id and self.company_state.services.get(idea.linked_service_id):
             print(f"[ServiceManager] Ideia '{idea.name}' (ID: {idea_id}) já possui um serviço associado (ID: {idea.linked_service_id}).")
             return self.company_state.services.get(idea.linked_service_id)

        service_name = initial_name or f"Serviço derivado de '{idea.name}'"
        service_description = initial_description or f"Serviço inicial baseado em: {idea.description}"

        new_service = Service(
            name=service_name,
            description=service_description,
            idea_id=idea.id
        )

        self.company_state.add_service(new_service) # Assumes CompanyState has add_service
        idea.linked_service_id = new_service.id
        # Não arquivar a ideia aqui, pois um serviço pode precisar de mais detalhes da ideia durante o escopo.
        # O workflow de serviço pode arquivar a ideia após o escopo.

        self.company_state.log_event(
            "SERVICE_DEFINED_FROM_IDEA",
            f"Serviço '{new_service.name}' definido a partir da ideia '{idea.name}'.",
            {"service_id": new_service.id, "idea_id": idea.id},
            source="ServiceManager"
        )
        print(f"[ServiceManager] Serviço '{new_service.name}' (ID: {new_service.id}) definido a partir da ideia '{idea.name}'.")
        return new_service

    def update_service_status(self, service_id: str, new_status_str: str, details: Optional[Dict] = None) -> bool:
        """
        Atualiza o status de um serviço.
        'new_status_str' deve ser um valor válido de ServiceStatus.
        """
        from src.core.service import ServiceStatus # Import local
        service = self.company_state.services.get(service_id)
        if not service:
            print(f"[ServiceManager] Serviço ID {service_id} não encontrado.")
            return False

        try:
            new_status_enum = ServiceStatus[new_status_str.upper()]
        except KeyError:
            # Tentativa de encontrar por valor se a chave falhar
            found_status = False
            for status_member in ServiceStatus:
                if status_member.value == new_status_str:
                    new_status_enum = status_member
                    found_status = True
                    break
            if not found_status:
                print(f"[ServiceManager] Status '{new_status_str}' inválido para Serviço.")
                return False

        service.update_status(new_status_enum, details)
        self.company_state.log_event(
            "SERVICE_STATUS_UPDATED",
            f"Status do serviço '{service.name}' atualizado para {new_status_enum.value}.",
            {"service_id": service.id, "new_status": new_status_enum.value, "details": details or {}},
            source="ServiceManager"
        )
        print(f"[ServiceManager] Status do serviço '{service.name}' (ID: {service.id}) atualizado para {new_status_enum.value}.")
        return True

    def define_service_scope(self, service_id: str, scope_details: str, effort_hours: float, price: float, skills: List[str]) -> bool:
        """
        Define (ou atualiza) o escopo de um serviço.
        """
        service = self.company_state.services.get(service_id)
        if not service:
            print(f"[ServiceManager] Serviço ID {service_id} não encontrado para definir escopo.")
            return False

        service.scope_details = scope_details
        service.estimated_effort_hours = effort_hours
        service.price_amount = price
        service.required_skills = skills

        from src.core.service import ServiceStatus # Import local
        if service.status in [ServiceStatus.PROPOSED, ServiceStatus.SCOPING]:
            service.update_status(ServiceStatus.READY_TO_OFFER, {"scope_defined_by": "ServiceManager"})

        self.company_state.log_event(
            "SERVICE_SCOPE_DEFINED",
            f"Escopo do serviço '{service.name}' definido/atualizado.",
            {"service_id": service.id, "effort_hours": effort_hours, "price": price},
            source="ServiceManager"
        )
        print(f"[ServiceManager] Escopo do serviço '{service.name}' (ID: {service.id}) definido.")
        return True
