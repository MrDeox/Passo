from typing import List, Optional, Any
# from src.core.company_state import CompanyState
# from src.core.product import Product, ProductStatus

class ProductCatalog:
    """
    Fornece funcionalidades para consultar o catálogo de produtos.
    """
    def __init__(self, company_state: Any):
        self.company_state = company_state

    def list_launched_products(self) -> List[Any]: # List[Product]
        """
        Retorna uma lista de todos os produtos lançados.
        """
        from src.core.product import ProductStatus # Import local
        launched = [p for p in self.company_state.products.values() if p.status == ProductStatus.LAUNCHED]
        print(f"[ProductCatalog] Encontrados {len(launched)} produtos lançados.")
        return launched

    def find_product_by_name(self, name: str) -> Optional[Any]: # Product
        """
        Encontra um produto pelo nome.
        """
        for product in self.company_state.products.values():
            if product.name.lower() == name.lower():
                print(f"[ProductCatalog] Produto '{name}' encontrado (ID: {product.id}).")
                return product
        print(f"[ProductCatalog] Produto com nome '{name}' não encontrado.")
        return None

    def get_product_details(self, product_id: str) -> Optional[Any]: # Product
        """
        Retorna os detalhes de um produto específico pelo ID.
        """
        product = self.company_state.products.get(product_id)
        if product:
            print(f"[ProductCatalog] Detalhes do produto ID {product_id} recuperados.")
        else:
            print(f"[ProductCatalog] Produto ID {product_id} não encontrado no catálogo.")
        return product
