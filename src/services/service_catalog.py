from typing import List, Optional, Any
# from src.core.company_state import CompanyState
# from src.core.service import Service, ServiceStatus

class ServiceCatalog:
    """
    Fornece funcionalidades para consultar o catálogo de serviços.
    """
    def __init__(self, company_state: Any):
        self.company_state = company_state

    def list_available_services(self) -> List[Any]: # List[Service]
        """
        Retorna uma lista de todos os serviços prontos para serem oferecidos.
        """
        from src.core.service import ServiceStatus # Import local
        available = [s for s in self.company_state.services.values() if s.status == ServiceStatus.READY_TO_OFFER]
        print(f"[ServiceCatalog] Encontrados {len(available)} serviços disponíveis para oferta.")
        return available

    def find_service_by_name(self, name: str) -> Optional[Any]: # Service
        """
        Encontra um serviço pelo nome.
        """
        for service in self.company_state.services.values():
            if service.name.lower() == name.lower():
                print(f"[ServiceCatalog] Serviço '{name}' encontrado (ID: {service.id}).")
                return service
        print(f"[ServiceCatalog] Serviço com nome '{name}' não encontrado.")
        return None

    def get_service_details(self, service_id: str) -> Optional[Any]: # Service
        """
        Retorna os detalhes de um serviço específico pelo ID.
        """
        service = self.company_state.services.get(service_id)
        if service:
            print(f"[ServiceCatalog] Detalhes do serviço ID {service_id} recuperados.")
        else:
            print(f"[ServiceCatalog] Serviço ID {service_id} não encontrado no catálogo.")
        return service
