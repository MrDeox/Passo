# -*- coding: utf-8 -*-
"""Esqueleto de um sistema para simular uma empresa digital.

Este módulo define classes e funções básicas para representar agentes
(equivalentes a funcionários ou bots) e locais da empresa. 

O objetivo é ter um ponto de partida para criação de interações mais
complexas no futuro.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# Dicionários globais para armazenar os agentes e os locais cadastrados.
agentes: Dict[str, "Agente"] = {}
locais: Dict[str, "Local"] = {}


@dataclass
class Local:
    """Representa um local na empresa.

    Attributes:
        nome: Nome do local (chave no dicionário global).
        descricao: Breve descrição do local.
        inventario: Lista de recursos ou ferramentas disponíveis.
        agentes_presentes: Lista de agentes atualmente neste local.
    """

    nome: str
    descricao: str
    inventario: List[str] = field(default_factory=list)
    agentes_presentes: List["Agente"] = field(default_factory=list)

    def adicionar_agente(self, agente: "Agente") -> None:
        """Adiciona um agente à lista de presentes."""
        if agente not in self.agentes_presentes:
            self.agentes_presentes.append(agente)

    def remover_agente(self, agente: "Agente") -> None:
        """Remove um agente da lista de presentes se estiver nela."""
        if agente in self.agentes_presentes:
            self.agentes_presentes.remove(agente)


@dataclass
class Agente:
    """Representa um agente da empresa."""

    nome: str
    funcao: str
    modelo_llm: str
    local_atual: Optional[Local] = None

    def mover_para(self, novo_local: Local) -> None:
        """Move o agente para um novo local, atualizando todas as referências."""
        if self.local_atual is not None:
            self.local_atual.remover_agente(self)
        novo_local.adicionar_agente(self)
        self.local_atual = novo_local


# ---------------------------------------------------------------------------
# Funções de manipulação de agentes e locais
# ---------------------------------------------------------------------------

def criar_agente(nome: str, funcao: str, modelo_llm: str, local: str) -> Agente:
    """Cria um novo agente e adiciona aos registros.

    Args:
        nome: Nome do agente.
        funcao: Cargo ou função do agente.
        modelo_llm: Modelo de LLM utilizado (ex.: "gpt-3.5-turbo").
        local: Nome do local onde o agente iniciará.

    Returns:
        O objeto ``Agente`` criado.
    """
    local_obj = locais.get(local)
    if local_obj is None:
        raise ValueError(f"Local '{local}' não encontrado.")

    agente = Agente(nome=nome, funcao=funcao, modelo_llm=modelo_llm, local_atual=local_obj)
    agentes[nome] = agente
    local_obj.adicionar_agente(agente)
    return agente


def criar_local(nome: str, descricao: str, inventario: Optional[List[str]] = None) -> Local:
    """Cria um novo local e adiciona aos registros."""
    local = Local(nome=nome, descricao=descricao, inventario=inventario or [])
    locais[nome] = local
    return local


def mover_agente(nome_agente: str, nome_novo_local: str) -> None:
    """Move um agente para outro local.

    Atualiza o ``local_atual`` do agente e as listas de ``agentes_presentes``
    tanto do local de origem quanto do novo local.
    """
    agente = agentes.get(nome_agente)
    if agente is None:
        raise ValueError(f"Agente '{nome_agente}' não encontrado.")

    novo_local = locais.get(nome_novo_local)
    if novo_local is None:
        raise ValueError(f"Local '{nome_novo_local}' não encontrado.")

    agente.mover_para(novo_local)


# ---------------------------------------------------------------------------
# Exemplo de uso
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Criar dois locais
    sala_reuniao = criar_local("Sala de Reunião", "Espaço para realizar reuniões", ["mesa", "projetor"])
    sala_tecnologia = criar_local("Sala de Tecnologia", "Laboratório de desenvolvimento", ["computadores", "ferramentas de rede"])

    # Criar três agentes
    alice = criar_agente("Alice", "Gerente", "gpt-3.5-turbo", "Sala de Reunião")
    bob = criar_agente("Bob", "Desenvolvedor", "deepseek-chat", "Sala de Tecnologia")
    carol = criar_agente("Carol", "Analista", "gpt-3.5-turbo", "Sala de Reunião")

    # Mover um agente entre salas
    mover_agente("Alice", "Sala de Tecnologia")

    # Exibir situação atual
    for local in locais.values():
        print(f"Agentes presentes em {local.nome}: {[ag.nome for ag in local.agentes_presentes]}")

