from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

# Faremos referência a CompanyState e LLMIntegration mais tarde
# from src.core.company_state import CompanyState
# from src.utils.llm_integration import LLMIntegration

class BaseAgent(ABC):
    """
    Classe base abstrata para todos os agentes de IA.
    """
    def __init__(self, name: str, role: str, llm_model: str, company_state: Any, llm_integration: Any):
        self.name = name
        self.role = role
        self.llm_model = llm_model
        self.company_state = company_state # Referência ao estado global da empresa
        self.llm_integration = llm_integration # Módulo para interagir com LLMs
        self.current_task: Optional[Any] = None # Tarefa atual do agente
        self.history: Dict[str, Any] = {"actions": [], "feedbacks": []}

    @abstractmethod
    async def perform_task(self) -> Any:
        """
        Método abstrato para o agente executar sua tarefa principal.
        Deve ser implementado por cada subclasse de agente.
        """
        pass

    async def send_prompt_to_llm(self, prompt: str) -> str:
        """
        Envia um prompt para o LLM configurado e retorna a resposta.
        Utiliza o módulo de integração LLM.
        """
        # return await self.llm_integration.generate_text(prompt, self.llm_model)
        # Placeholder até llm_integration ser definido
        print(f"Agente {self.name} ({self.role}) enviando prompt (modelo {self.llm_model}): {prompt[:100]}...")
        return f"Resposta simulada do LLM para: {prompt[:50]}"

    def update_history(self, action: str, result: Any):
        """
        Atualiza o histórico de ações do agente.
        """
        self.history["actions"].append({"action": action, "result": result, "timestamp": self.company_state.current_time}) # Assumindo que company_state tem current_time

    def receive_feedback(self, feedback: str):
        """
        Recebe feedback (ex: do CEC ou de um workflow).
        """
        self.history["feedbacks"].append({"feedback": feedback, "timestamp": self.company_state.current_time})

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', role='{self.role}', llm_model='{self.llm_model}')"
