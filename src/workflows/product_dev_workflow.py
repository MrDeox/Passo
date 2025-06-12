from typing import Any, Optional, Dict, List
from enum import Enum
from .base_workflow import BaseWorkflow, WorkflowStatus
from src.core.idea import IdeaStatus # Import directly as it's used in __init__ or method signature
# from src.core.product import Product, ProductStatus
# from src.agents.execution_agent import ExecutionAgent
# from src.agents.marketing_agent import MarketingAgent

class ProductDevelopmentWorkflow(BaseWorkflow):
    """
    Gerencia o ciclo de vida de desenvolvimento de um produto,
    desde uma ideia validada até o lançamento.
    """
    def __init__(self, workflow_id: str, company_state: Any, idea_id: str, settings: Optional[Dict] = None):
        super().__init__(workflow_id, company_state, settings)
        self.idea_id = idea_id
        self.product_id: Optional[str] = None

    async def run(self) -> bool:
        self._set_status(WorkflowStatus.RUNNING, f"Iniciando workflow de desenvolvimento de produto para ideia ID: {self.idea_id}.")

        idea = self.company_state.get_idea(self.idea_id)
        if not idea or idea.status != IdeaStatus.VALIDATED_APPROVED:
            self._set_status(WorkflowStatus.FAILED, f"Ideia ID {self.idea_id} não encontrada ou não aprovada.")
            return False

        self._log_step("initiation", f"Iniciando com base na ideia aprovada: '{idea.name}'.")

        # Passo 1: Criar a entidade Produto
        from src.core.product import Product, ProductStatus # Import local

        new_product = Product(name=f"Produto de {idea.name}", description=f"Versão inicial do produto baseado em {idea.description}", idea_id=idea.id)
        self.company_state.add_product(new_product)
        self.product_id = new_product.id
        if idea: # Check if idea exists before trying to update it
            idea.linked_product_id = self.product_id
        self._log_step("product_creation", f"Produto '{new_product.name}' (ID: {self.product_id}) criado a partir da ideia.", {"product_id": self.product_id})

        # Passo 2: Desenvolvimento (simulado)
        self._log_step("development_start", f"Iniciando desenvolvimento do produto '{new_product.name}'.")
        new_product.update_status(ProductStatus.DEVELOPMENT, {"workflow_id": self.workflow_id})
        new_product.version = "1.0.0"
        new_product.update_status(ProductStatus.READY_FOR_LAUNCH, {"workflow_id": self.workflow_id, "version": "1.0.0"})
        self._log_step("development_complete", f"Desenvolvimento do produto '{new_product.name}' concluído. Versão: {new_product.version}.", {"product_id": self.product_id})

        # Passo 3: Preparação para Lançamento (Marketing - simulado)
        self._log_step("marketing_prep_start", f"Iniciando preparação de marketing para '{new_product.name}'.")
        new_product.marketing_materials_ids.append(f"marketing_doc_{self.product_id}")
        self._log_step("marketing_prep_complete", f"Materiais de marketing para '{new_product.name}' preparados.", {"product_id": self.product_id})

        # Passo 4: Lançamento (simulado)
        new_product.update_status(ProductStatus.LAUNCHED, {"workflow_id": self.workflow_id})
        self.company_state.balance += 1000
        self.company_state.log_event("PRODUCT_LAUNCHED", f"Produto '{new_product.name}' lançado!", {"product_id": self.product_id, "initial_revenue_sim": 1000})
        self._log_step("product_launch", f"Produto '{new_product.name}' lançado com sucesso!", {"product_id": self.product_id})

        self._set_status(WorkflowStatus.COMPLETED, f"Workflow de desenvolvimento do produto '{new_product.name}' concluído.")
        return True
