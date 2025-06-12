from typing import Optional, Dict, Any
# from src.core.company_state import CompanyState
# from src.core.idea import Idea, IdeaStatus
# from src.core.product import Product, ProductStatus

class ProductManager:
    """
    Gerencia a lógica de criação e ciclo de vida de produtos.
    """
    def __init__(self, company_state: Any):
        self.company_state = company_state

    def create_product_from_idea(self, idea_id: str, initial_name: Optional[str] = None, initial_description: Optional[str] = None) -> Optional[Any]: # Product
        """
        Cria uma nova entidade Product com base em uma Idea aprovada.
        """
        idea = self.company_state.get_idea(idea_id) # Assumes CompanyState has get_idea

        # Import local para evitar problemas de importação circular no nível do módulo
        from src.core.idea import IdeaStatus
        from src.core.product import Product, ProductStatus

        if not idea:
            print(f"[ProductManager] Ideia ID {idea_id} não encontrada.")
            return None

        if idea.status != IdeaStatus.VALIDATED_APPROVED:
            print(f"[ProductManager] Ideia '{idea.name}' (ID: {idea_id}) não está aprovada para desenvolvimento de produto (status: {idea.status.value}).")
            return None

        if idea.linked_product_id and self.company_state.products.get(idea.linked_product_id):
             print(f"[ProductManager] Ideia '{idea.name}' (ID: {idea_id}) já possui um produto associado (ID: {idea.linked_product_id}).")
             return self.company_state.products.get(idea.linked_product_id)

        product_name = initial_name or f"Produto derivado de '{idea.name}'"
        product_description = initial_description or f"Descrição inicial para o produto baseado em: {idea.description}"

        new_product = Product(
            name=product_name,
            description=product_description,
            idea_id=idea.id
            # Outros atributos podem ser definidos aqui ou através de workflows
        )

        self.company_state.add_product(new_product) # Assumes CompanyState has add_product
        idea.linked_product_id = new_product.id
        idea.update_status(IdeaStatus.ARCHIVED, {"reason": "Convertida em produto", "product_id": new_product.id}) # Arquiva a ideia

        self.company_state.log_event(
            "PRODUCT_CREATED_FROM_IDEA",
            f"Produto '{new_product.name}' criado a partir da ideia '{idea.name}'.",
            {"product_id": new_product.id, "idea_id": idea.id},
            source="ProductManager"
        )
        print(f"[ProductManager] Produto '{new_product.name}' (ID: {new_product.id}) criado a partir da ideia '{idea.name}'.")
        return new_product

    def update_product_status(self, product_id: str, new_status_str: str, details: Optional[Dict] = None) -> bool:
        """
        Atualiza o status de um produto.
        'new_status_str' deve ser um valor válido de ProductStatus.
        """
        from src.core.product import ProductStatus # Import local
        product = self.company_state.products.get(product_id)
        if not product:
            print(f"[ProductManager] Produto ID {product_id} não encontrado.")
            return False

        try:
            new_status_enum = ProductStatus[new_status_str.upper()]
        except KeyError:
            # Tentativa de encontrar por valor se a chave falhar (ex: "EM DESENVOLVIMENTO" vs "DEVELOPMENT")
            found_status = False
            for status_member in ProductStatus:
                if status_member.value == new_status_str:
                    new_status_enum = status_member
                    found_status = True
                    break
            if not found_status:
                print(f"[ProductManager] Status '{new_status_str}' inválido para Produto.")
                return False

        product.update_status(new_status_enum, details)
        self.company_state.log_event(
            "PRODUCT_STATUS_UPDATED",
            f"Status do produto '{product.name}' atualizado para {new_status_enum.value}.",
            {"product_id": product.id, "new_status": new_status_enum.value, "details": details or {}},
            source="ProductManager"
        )
        print(f"[ProductManager] Status do produto '{product.name}' (ID: {product.id}) atualizado para {new_status_enum.value}.")
        return True

    # Outras funções: set_price, record_sale, manage_inventory (se aplicável), etc.
