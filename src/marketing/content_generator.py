from typing import Any, Optional, Dict, List # Added List
from dataclasses import dataclass, field # Adicionado para MarketingContent
import uuid # Adicionado para MarketingContent
import time # Adicionado para MarketingContent

# from src.core.company_state import CompanyState

@dataclass
class MarketingContent:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    creation_timestamp: float = field(default_factory=time.time)
    content_type: str
    title: Optional[str] = None
    body: str
    author_agent_name: Optional[str] = None
    related_campaign_id: Optional[str] = None
    related_item_id: Optional[str] = None

class ContentGenerator:
    """
    Responsável por gerar (ou coordenar a geração de) conteúdo de marketing.
    """
    def __init__(self, company_state: Any, llm_integration: Optional[Any] = None):
        self.company_state = company_state
        self.llm_integration = llm_integration
        if not hasattr(self.company_state, 'marketing_contents'):
            self.company_state.marketing_contents = {}

    async def generate_blog_post_for_product(self, product_id: str, author_agent: Optional[Any] = None) -> Optional[MarketingContent]:
        product = self.company_state.products.get(product_id)
        if not product:
            print(f"[ContentGenerator] Produto ID {product_id} não encontrado para gerar blog post.")
            return None

        prompt = f"Escreva um post de blog otimista e informativo sobre o lançamento do nosso novo produto: '{product.name}'. Detalhes do produto: {product.description}. Destaque seus principais benefícios e um call-to-action."

        blog_body = ""
        generated_by = "ContentGenerator_RuleBased"

        if author_agent:
            blog_body = f"Conteúdo gerado pelo agente {author_agent.name} para '{product.name}' (simulado)."
            generated_by = author_agent.name
        elif self.llm_integration:
            blog_body = f"Conteúdo gerado por LLM para '{product.name}' (simulado)."
            generated_by = "ContentGenerator_LLM"
        else:
            blog_body = f"Este é um post de blog sobre o incrível produto '{product.name}'. Ele faz maravilhas e você deveria comprá-lo agora! {product.description}"

        content = MarketingContent(
            content_type="blog_post",
            title=f"Conheça o Novo {product.name}!",
            body=blog_body,
            author_agent_name=generated_by,
            related_item_id=product.id
        )
        self.company_state.marketing_contents[content.id] = content

        self.company_state.log_event(
            "MARKETING_CONTENT_GENERATED",
            f"Conteúdo de marketing '{content.title}' gerado para produto '{product.name}'.",
            content.__dict__,
            source=generated_by
        )
        print(f"[ContentGenerator] Blog post '{content.title}' gerado para produto '{product.name}'.")
        return content
