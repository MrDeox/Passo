from dataclasses import dataclass, field # field might be needed if Ideia uses default_factory
from typing import Optional, List, Dict # For attributes of Ideia and other future types

@dataclass
class Ideia:
    descricao: str
    justificativa: str
    autor: str # Nome do agente que propôs a ideia
    validada: bool = False
    executada: bool = False # Se a prototipagem/execução já ocorreu
    resultado: float = 0.0  # Resultado financeiro da ideia após execução/prototipagem
    link_produto: Optional[str] = None # Link para o produto na Gumroad, se criado

    # Adicionar outros campos relevantes que possam ter sido adicionados em Ideia
    # Por exemplo, se complexidade, potencial_lucro, prioridade foram adicionados antes
    # complexidade: int = 1
    # potencial_lucro: int = 1
    # prioridade: int = 1
    # No estado atual do código, esses campos extras não existem na definição principal de Ideia.

    # Se Ideia precisar de métodos ou ser mais complexa, pode evoluir aqui.
    # Por agora, é uma simples dataclass para transferência de dados.

# Poderíamos também mover outras dataclasses compartilhadas aqui no futuro,
# como definições base para Agente ou Local, se isso ajudar a quebrar outras dependências,
# mas por agora, apenas Ideia é o foco para resolver a dependência circular imediata.

# O histórico_ideias e preferencia_temas permanecem em ciclo_criativo.py por enquanto,
# pois são estados globais daquele módulo. As funções de salvar/carregar
# também permanecem lá, operando nesse estado global.
# empresa_digital.py chama essas funções, o que é uma dependência aceitável.
# O problema principal era a dependência de tipo (Ideia) entre os módulos.
