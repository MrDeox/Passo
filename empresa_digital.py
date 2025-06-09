# -*- coding: utf-8 -*-
"""Esqueleto de um sistema para simular uma empresa digital.

Este módulo define classes e funções básicas para representar agentes
(equivalentes a funcionários ou bots) e locais da empresa.

O objetivo é ter um ponto de partida para criação de interações mais
complexas no futuro.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import json

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


def criar_agente(
    nome: str, funcao: str, modelo_llm: str, local: str
) -> Agente:
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

    agente = Agente(
        nome=nome, funcao=funcao, modelo_llm=modelo_llm, local_atual=local_obj
    )
    agentes[nome] = agente
    local_obj.adicionar_agente(agente)
    return agente


def criar_local(
    nome: str, descricao: str, inventario: Optional[List[str]] = None
) -> Local:
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


def salvar_dados(arquivo_agentes: str, arquivo_locais: str) -> None:
    """Salva os dicionários globais de agentes e locais em arquivos JSON.

    Somente informações necessárias para reconstrução dos objetos são
    persistidas (nome do local em que cada agente está, por exemplo).
    """

    # Serializa agentes registrando apenas dados essenciais e o nome do local
    dados_agentes = {
        nome: {
            "nome": ag.nome,
            "funcao": ag.funcao,
            "modelo_llm": ag.modelo_llm,
            "local_atual": ag.local_atual.nome if ag.local_atual else None,
        }
        for nome, ag in agentes.items()
    }
    with open(arquivo_agentes, "w", encoding="utf-8") as f:
        json.dump(dados_agentes, f, ensure_ascii=False, indent=2)

    # Serializa locais ignorando a lista de agentes presentes, pois ela será
    # reconstruída ao carregar os agentes
    dados_locais = {
        nome: {
            "nome": loc.nome,
            "descricao": loc.descricao,
            "inventario": loc.inventario,
        }
        for nome, loc in locais.items()
    }
    with open(arquivo_locais, "w", encoding="utf-8") as f:
        json.dump(dados_locais, f, ensure_ascii=False, indent=2)


def carregar_dados(arquivo_agentes: str, arquivo_locais: str) -> None:
    """Carrega arquivos JSON recriando os dicionários de agentes e locais."""

    global agentes, locais
    agentes = {}
    locais = {}

    # Carrega primeiro os locais, pois os agentes dependem deles
    with open(arquivo_locais, "r", encoding="utf-8") as f:
        dados_locais = json.load(f)
    for info in dados_locais.values():
        criar_local(info["nome"], info["descricao"], info.get("inventario"))

    # Agora recria os agentes e os adiciona aos locais correspondentes
    with open(arquivo_agentes, "r", encoding="utf-8") as f:
        dados_agentes = json.load(f)
    for info in dados_agentes.values():
        criar_agente(
            info["nome"],
            info["funcao"],
            info["modelo_llm"],
            info.get("local_atual") or "",
        )


def gerar_prompt_dinamico(agente: Agente) -> str:
    """Gera uma descrição textual da situação atual de um agente."""

    if agente.local_atual is None:
        return f"Agente {agente.nome} está sem local definido."

    local = agente.local_atual
    colegas = [a.nome for a in local.agentes_presentes if a is not agente]

    partes = [
        f"Agente: {agente.nome}",
        f"Função: {agente.funcao}",
        f"Local: {local.nome}",
        f"Descrição do local: {local.descricao}",
        (
            "Colegas presentes: "
            + (", ".join(colegas) if colegas else "Nenhum")
        ),
        (
            "Inventário disponível: "
            + (", ".join(local.inventario) if local.inventario else "Nenhum")
        ),
    ]
    return "\n".join(partes)


# ---------------------------------------------------------------------------
# Exemplo de uso
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Criar dois locais
    sala_reuniao = criar_local(
        "Sala de Reunião",
        "Espaço para realizar reuniões",
        ["mesa", "projetor"],
    )
    sala_tecnologia = criar_local(
        "Sala de Tecnologia",
        "Laboratório de desenvolvimento",
        ["computadores", "ferramentas de rede"],
    )

    # Criar três agentes
    alice = criar_agente(
        "Alice", "Gerente", "gpt-3.5-turbo", "Sala de Reunião"
    )
    bob = criar_agente(
        "Bob", "Desenvolvedor", "deepseek-chat", "Sala de Tecnologia"
    )
    carol = criar_agente(
        "Carol", "Analista", "gpt-3.5-turbo", "Sala de Reunião"
    )

    # Mover um agente entre salas
    mover_agente("Alice", "Sala de Tecnologia")

    # Exibir situação atual com prompts dinâmicos
    for agente in agentes.values():
        print("\n" + gerar_prompt_dinamico(agente))

    # Persistir o estado em disco
    salvar_dados("agentes.json", "locais.json")

    # Limpar registros e recarregar do disco para demonstrar a função
    agentes.clear()
    locais.clear()
    carregar_dados("agentes.json", "locais.json")

    print("\nEstado restaurado do disco:")
    for agente in agentes.values():
        print(f"- {agente.nome} está em {agente.local_atual.nome}")
