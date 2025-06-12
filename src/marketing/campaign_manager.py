from typing import Any, Optional, Dict, List
from enum import Enum
import uuid
import time
from dataclasses import dataclass, field # Adicionado para MarketingCampaign

# from src.core.company_state import CompanyState

class CampaignStatus(Enum):
    PLANNING = "EM PLANEJAMENTO"
    ACTIVE = "ATIVA"
    COMPLETED = "CONCLUÍDA"
    CANCELLED = "CANCELADA"

@dataclass
class MarketingCampaign:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    status: CampaignStatus = CampaignStatus.PLANNING
    start_date: Optional[float] = None
    end_date: Optional[float] = None
    budget: float = 0.0
    target_audience: Optional[str] = None
    target_item_id: Optional[str] = None
    target_item_type: Optional[str] = None
    goals: List[str] = field(default_factory=list)
    results: Dict[str, Any] = field(default_factory=dict)
    content_ids: List[str] = field(default_factory=list)

class CampaignManager:
    """
    Gerencia a criação, execução e monitoramento de campanhas de marketing.
    """
    def __init__(self, company_state: Any):
        self.company_state = company_state
        if not hasattr(self.company_state, 'marketing_campaigns'):
            self.company_state.marketing_campaigns = {}


    def create_campaign(self, name: str, budget: float, target_item_id: str, target_item_type: str, goals: List[str], target_audience: Optional[str] = None) -> Optional[MarketingCampaign]:
        item_exists = False
        if target_item_type == "Product" and self.company_state.products.get(target_item_id):
            item_exists = True
        elif target_item_type == "Service" and self.company_state.services.get(target_item_id):
            item_exists = True

        if not item_exists:
            print(f"[CampaignManager] Item alvo '{target_item_type}' com ID '{target_item_id}' não encontrado.")
            self.company_state.log_event("MARKETING_CAMPAIGN_CREATE_FAILED", f"Item alvo {target_item_type} ID {target_item_id} não encontrado.", {"name": name}, "CampaignManager")
            return None

        campaign = MarketingCampaign(
            name=name,
            budget=budget,
            target_item_id=target_item_id,
            target_item_type=target_item_type,
            goals=goals,
            target_audience=target_audience
        )
        self.company_state.marketing_campaigns[campaign.id] = campaign

        self.company_state.log_event(
            "MARKETING_CAMPAIGN_CREATED",
            f"Campanha de marketing '{campaign.name}' criada.",
            campaign.__dict__,
            source="CampaignManager"
        )
        print(f"[CampaignManager] Campanha '{campaign.name}' (ID: {campaign.id}) criada.")
        return campaign

    def launch_campaign(self, campaign_id: str) -> bool:
        campaign = self.company_state.marketing_campaigns.get(campaign_id)
        if not campaign:
            print(f"[CampaignManager] Campanha ID {campaign_id} não encontrada.")
            return False

        if campaign.status != CampaignStatus.PLANNING:
            print(f"[CampaignManager] Campanha '{campaign.name}' não está em planejamento (status: {campaign.status.value}).")
            return False

        campaign.status = CampaignStatus.ACTIVE
        campaign.start_date = self.company_state.current_time

        self.company_state.log_event(
            "MARKETING_CAMPAIGN_LAUNCHED",
            f"Campanha '{campaign.name}' lançada.",
            {"campaign_id": campaign.id, "budget": campaign.budget},
            source="CampaignManager"
        )
        print(f"[CampaignManager] Campanha '{campaign.name}' (ID: {campaign.id}) lançada.")
        return True
