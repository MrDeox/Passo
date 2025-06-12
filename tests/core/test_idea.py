import pytest
import time
from src.core.idea import Idea, IdeaStatus

def test_idea_creation_defaults():
    """Testa a criação de uma Idea com valores padrão."""
    idea_name = "Nova Ideia Fantástica"
    idea_desc = "Uma descrição detalhada desta ideia."
    idea = Idea(name=idea_name, description=idea_desc)

    assert idea.name == idea_name
    assert idea.description == idea_desc
    assert idea.status == IdeaStatus.PROPOSED
    assert idea.author_agent_name is None
    assert idea.validation_details == {}
    assert idea.linked_product_id is None
    assert idea.linked_service_id is None
    assert len(idea.id) == 36 # UUID length
    assert time.time() - idea.creation_timestamp < 1 # Criado recentemente

def test_idea_update_status():
    """Testa a atualização de status de uma Idea."""
    idea = Idea(name="Ideia para Testar Status", description="Testando mudança de status.")
    initial_timestamp = idea.creation_timestamp

    time.sleep(0.01) # Pequeno delay para garantir que o timestamp mude

    new_status = IdeaStatus.VALIDATED_APPROVED
    details = {"validator_agent": "ValidadorX", "score": 9}
    idea.update_status(new_status, details)

    assert idea.status == new_status
    assert len(idea.history) == 1
    history_entry = idea.history[0]
    assert history_entry["old_status"] == IdeaStatus.PROPOSED.value
    assert history_entry["new_status"] == new_status.value
    assert history_entry["details"]["validator_agent"] == "ValidadorX"
    assert history_entry["details"]["score"] == 9
    assert history_entry["timestamp"] > initial_timestamp

def test_idea_custom_author():
    """Testa a criação de uma Idea com um autor."""
    author = "AgenteCriativo007"
    idea = Idea(name="Ideia com Autor", description="Desc", author_agent_name=author)
    assert idea.author_agent_name == author
