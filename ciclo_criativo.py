import logging
from dataclasses import asdict # dataclass is now in core_types
from typing import List, Dict, Optional
import json # Added for saving/loading historico_ideias

import empresa_digital as ed
from .core_types import Ideia # Import Ideia from core_types
from .criador_de_produtos import produto_digital
from .divulgador import sugerir_conteudo_marketing # Import for Divulgador

logger = logging.getLogger(__name__)

# Ideia dataclass definition is removed from here

historico_ideias: List[Ideia] = [] # Now uses Ideia from core_types
preferencia_temas: Dict[str, int] = {}


def salvar_historico_ideias(filename="historico_ideias.json"):
    """Salva o historico_ideias em um arquivo JSON."""
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            # Convert Ideia objects to dictionaries for JSON serialization
            json.dump([asdict(ideia) for ideia in historico_ideias], f, ensure_ascii=False, indent=4)
        logger.info(f"Histórico de ideias salvo em {filename}")
    except IOError as e:
        logger.error(f"Erro ao salvar histórico de ideias: {e}")

def carregar_historico_ideias(filename="historico_ideias.json") -> List[Ideia]:
    """Carrega o historico_ideias de um arquivo JSON."""
    global historico_ideias # Allow modification of the global variable
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            ideias_data = json.load(f)
            # Convert dictionaries back to Ideia objects
            historico_ideias = [Ideia(**data) for data in ideias_data]
            logger.info(f"Histórico de ideias carregado de {filename}")
            return historico_ideias
    except FileNotFoundError:
        logger.warning(f"Arquivo de histórico de ideias '{filename}' não encontrado. Iniciando com histórico vazio.")
        historico_ideias = []
        return []
    except json.JSONDecodeError as e:
        logger.error(f"Erro ao decodificar JSON do histórico de ideias: {e}. Iniciando com histórico vazio.")
        historico_ideias = []
        return []
    except Exception as e: # Catch other potential errors during loading (e.g., TypeError if Ideia structure changed)
        logger.error(f"Erro inesperado ao carregar histórico de ideias: {e}. Iniciando com histórico vazio.")
        historico_ideias = []
        return []


def _tema_preferido() -> str:
    """Define o tema a ser priorizado conforme resultados anteriores."""
    if not preferencia_temas:
        return "IA"
    return max(preferencia_temas, key=preferencia_temas.get)


def propor_ideias() -> List[Ideia]:
    """Gera ideias simuladas a partir de agentes com funcao 'Ideacao'."""
    ideias = []
    tema = _tema_preferido()
    for ag in ed.agentes.values():
        if ag.funcao.lower() == "ideacao":
            desc = f"Produto {tema} proposto por {ag.nome}"
            justificativa = f"Explora {tema} com alto potencial de lucro"
            ideia = Ideia(descricao=desc, justificativa=justificativa, autor=ag.nome)
            ideias.append(ideia)
            logger.info("Ideia proposta: %s", desc)
            ed.registrar_evento(f"Ideia proposta: {desc}")
    return ideias


def validar_ideias(ideias: List[Ideia]) -> None:
    """Valida as ideias usando agentes com funcao 'Validador'."""
    validadores = [a for a in ed.agentes.values() if a.funcao.lower() == "validador"]
    for ideia in ideias:
        for val in validadores:
            aprovado = "ia" in ideia.descricao.lower()
            logger.info(
                "Validacao de %s por %s: %s",
                ideia.descricao,
                val.nome,
                "aprovada" if aprovado else "reprovada",
            )
            ed.registrar_evento(
                f"Validacao de {ideia.descricao} por {val.nome}: {'aprovada' if aprovado else 'reprovada'}"
            )
            if aprovado:
                ideia.validada = True
                ed.adicionar_tarefa(ideia.descricao)
                break


def prototipar_ideias(ideias: List[Ideia]) -> None:
    """Simula prototipagem gerando lucro ou prejuizo."""
    for ideia in ideias:
        if not ideia.validada:
            continue

        # Tentativa de criar produto digital se ainda não foi criado
        if ideia.link_produto is None:
            logger.info(f"Tentando criar produto digital para ideia validada: {ideia.descricao}")
            try:
                # ed.agentes e ed.locais são acessados globalmente a partir de empresa_digital importado como ed
                product_url = produto_digital(ideia, ed.agentes, ed.locais)
                if product_url:
                    ideia.link_produto = product_url
                    # Evento de criação de produto já é registrado em produto_digital.py
                    logger.info(f"Produto '{ideia.descricao}' criado com sucesso: {product_url}")

                    # >>> Integration of Divulgador <<<
                    logger.info(f"Tentando gerar sugestões de marketing para '{ideia.descricao}'...")
                    marketing_sugestoes = sugerir_conteudo_marketing(ideia, product_url)
                    if marketing_sugestoes:
                        # Logging e registro de evento são feitos dentro de sugerir_conteudo_marketing
                        logger.info(f"Sugestões de marketing geradas para '{ideia.descricao}'.")
                    else:
                        logger.warning(f"Não foram geradas sugestões de marketing para '{ideia.descricao}'.")
                    # >>> End Integration of Divulgador <<<

                    # Atualiza resultado da ideia com base na criação do produto
                    # A lógica de bônus aqui é um exemplo e pode ser ajustada.
                    # Removemos o bônus anterior de "sucesso" genérico se o produto foi criado.
                    ideia.resultado = 50.0 # Base result for successful product creation
                    if "ia" in ideia.descricao.lower(): # Bônus adicional para produtos de IA
                        ideia.resultado += 25.0
                    if "produto" in ideia.descricao.lower(): # Bônus adicional se a palavra "produto" estiver na descrição
                        ideia.resultado += 10.0
                else:
                    logger.error(f"Falha ao criar produto digital para a ideia: {ideia.descricao}")
                    ed.registrar_evento(f"Falha na criação do produto para ideia: {ideia.descricao}")
                    ideia.resultado = -15.0 # Penalidade maior se a criação do produto falhar
            except Exception as e:
                logger.error(f"Exceção ao tentar criar produto digital para '{ideia.descricao}': {e}", exc_info=True)
                ed.registrar_evento(f"Exceção na criação do produto para ideia '{ideia.descricao}': {e}")
                ideia.resultado = -20.0 # Penalidade por exceção

        # Lógica de simulação de prototipagem/resultado (executada mesmo se o produto já existia ou falhou, mas com resultado já ajustado)
        if not ideia.executada:
            ideia.executada = True
            # Se o resultado não foi definido pela lógica de criação de produto (ex: ideia já tinha link_produto)
            # ou se queremos adicionar mais alguma lógica de resultado baseada em 'sucesso'
            if ideia.resultado == 0.0 and not ideia.link_produto : # Só aplica resultado padrão se não foi tocado pela criação de produto.
                sucesso_prototipagem = "ia" in ideia.descricao.lower() # Condição de sucesso original
                ideia.resultado = 30.0 if sucesso_prototipagem else -10.0

            tema = "IA" if "ia" in ideia.descricao.lower() else "outros" # TODO: Melhorar extração de tema
            preferencia_temas[tema] = preferencia_temas.get(tema, 0) + (1 if sucesso else -1)
            logger.info(
                "Prototipo/Execução de %s resultou em %.2f (Link produto: %s)",
                ideia.descricao,
                ideia.resultado,
                ideia.link_produto if ideia.link_produto else "N/A"
            )
            ed.registrar_evento(
                f"Prototipo/Execução de {ideia.descricao} resultou em {ideia.resultado:.2f}. Link: {ideia.link_produto if ideia.link_produto else 'N/A'}"
            )


def executar_ciclo_criativo() -> None:
    """Executa um ciclo completo de ideacao, validacao e prototipagem."""
    ideias = propor_ideias()
    if not ideias:
        if ed.MODO_VIDA_INFINITA:
            ed.registrar_evento("VIDA INFINITA: Gerando 3 ideias automáticas.")
            logger.info("VIDA INFINITA: Nenhuma ideia proposta por agentes. Gerando 3 ideias automáticas.")
            ideias_automaticas = [
                Ideia(
                    descricao="Ideia automática VIDA INFINITA: Super App Inovador",
                    justificativa="Dominar todos os nichos de mercado com um único app.",
                    autor="Sistema Criativo Infinito"
                ),
                Ideia(
                    descricao="Ideia automática VIDA INFINITA: Colonização Espacial",
                    justificativa="Expandir os horizontes da empresa para além da Terra.",
                    autor="Sistema Criativo Infinito"
                ),
                Ideia(
                    descricao="Ideia automática VIDA INFINITA: IA Consciente",
                    justificativa="Criar a primeira inteligência artificial verdadeiramente senciente.",
                    autor="Sistema Criativo Infinito"
                )
            ]
            ideias.extend(ideias_automaticas)
        else:
            # This is the existing logic from the previous step
            ideia_automatica = Ideia(
                descricao="Ideia genérica de otimização de processos internos",
                justificativa="Manter o fluxo de inovação e buscar melhorias contínuas quando nenhuma outra ideia for proposta.",
                autor="Sistema Criativo Automático"
            )
            ideias.append(ideia_automatica)
            ed.registrar_evento(f"Ideia automática gerada: {ideia_automatica.descricao}")
            logger.info("Nenhuma ideia proposta por agentes. Gerada ideia automática: %s", ideia_automatica.descricao)
    validar_ideias(ideias)
    prototipar_ideias(ideias)
    historico_ideias.extend(ideias)
    # Ao final do ciclo, poderíamos salvar o histórico, mas isso pode ser feito centralmente em empresa_digital.py
    # salvar_historico_ideias() # Opcional: salvar a cada ciclo
