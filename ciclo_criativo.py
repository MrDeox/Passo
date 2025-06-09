import logging
from dataclasses import dataclass
from typing import List, Dict

from empresa_digital import agentes, adicionar_tarefa

logger = logging.getLogger(__name__)

@dataclass
class Ideia:
    descricao: str
    justificativa: str
    autor: str
    validada: bool = False
    executada: bool = False
    resultado: float = 0.0

historico_ideias: List[Ideia] = []
preferencia_temas: Dict[str, int] = {}


def _tema_preferido() -> str:
    """Define o tema a ser priorizado conforme resultados anteriores."""
    if not preferencia_temas:
        return "IA"
    return max(preferencia_temas, key=preferencia_temas.get)


def propor_ideias() -> List[Ideia]:
    """Gera ideias simuladas a partir de agentes com funcao 'Ideacao'."""
    ideias = []
    tema = _tema_preferido()
    for ag in agentes.values():
        if ag.funcao.lower() == "ideacao":
            desc = f"Produto {tema} proposto por {ag.nome}"
            justificativa = f"Explora {tema} com alto potencial de lucro"
            ideia = Ideia(descricao=desc, justificativa=justificativa, autor=ag.nome)
            ideias.append(ideia)
            logger.info("Ideia proposta: %s", desc)
    return ideias


def validar_ideias(ideias: List[Ideia]) -> None:
    """Valida as ideias usando agentes com funcao 'Validador'."""
    validadores = [a for a in agentes.values() if a.funcao.lower() == "validador"]
    for ideia in ideias:
        for val in validadores:
            aprovado = "ia" in ideia.descricao.lower()
            logger.info(
                "Validacao de %s por %s: %s",
                ideia.descricao,
                val.nome,
                "aprovada" if aprovado else "reprovada",
            )
            if aprovado:
                ideia.validada = True
                adicionar_tarefa(ideia.descricao)
                break


def prototipar_ideias(ideias: List[Ideia]) -> None:
    """Simula prototipagem gerando lucro ou prejuizo."""
    for ideia in ideias:
        if not ideia.validada:
            continue
        sucesso = "ia" in ideia.descricao.lower()
        ideia.executada = True
        ideia.resultado = 30.0 if sucesso else -10.0
        tema = "IA" if "ia" in ideia.descricao.lower() else "outros"
        preferencia_temas[tema] = preferencia_temas.get(tema, 0) + (1 if sucesso else -1)
        logger.info(
            "Prototipo de %s resultou em %.2f",
            ideia.descricao,
            ideia.resultado,
        )


def executar_ciclo_criativo() -> None:
    """Executa um ciclo completo de ideacao, validacao e prototipagem."""
    ideias = propor_ideias()
    validar_ideias(ideias)
    prototipar_ideias(ideias)
    historico_ideias.extend(ideias)
