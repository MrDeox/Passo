import logging
from typing import List, Dict # 'Any' is no longer needed here
from core_types import Ideia, Service, Task, Agente, Local # Added Agente and Local

# From ciclo_criativo.py
historico_ideias: List[Ideia] = []
historico_servicos: List[Service] = []
preferencia_temas: Dict[str, int] = {}

# From empresa_digital.py
saldo: float = 0.0
historico_saldo: List[float] = []
tarefas_pendentes: List[Task] = []
agentes: Dict[str, Agente] = {}  # Updated to use Agente type
locais: Dict[str, Local] = {}   # Updated to use Local type
historico_eventos: List[str] = []
ciclo_atual_simulacao: int = 0
MODO_VIDA_INFINITA: bool = False # Added for runtime changes

# Moved from empresa_digital.py
logger_state = logging.getLogger(__name__) # Use a distinct logger name if desired, or pass logger

def registrar_evento(msg: str) -> None:
    historico_eventos.append(msg)
    # Use logger_state to avoid confusion with other loggers if this file is imported elsewhere
    logger_state.info("EVENTO: %s", msg)
