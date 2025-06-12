import logging
import os
# import json # May not be needed if LLM response is treated as raw string

import state # Added
from core_types import Ideia, Agente # Changed from empresa_digital
# registrar_evento will be imported from state or use state.registrar_evento
from openrouter_utils import selecionar_modelo, chamar_openrouter_api
# from state import registrar_evento # Option 1 for registrar_evento

# Module-level logger
logger = logging.getLogger(__name__)

# --- Integration Point Comment ---
# The `sugerir_conteudo_marketing` function defined below is intended to be called
# after a digital product has been successfully created and its link is available.
# A likely place for this call would be in `ciclo_criativo.py`, within the
# `prototipar_ideias` function, after `produto_digital()` returns a valid product URL.
# Example call from `ciclo_criativo.py`:
#
# if product_url: # After successful product creation
#     ideia.link_produto = product_url
#     logger.info(f"Produto digital criado com sucesso para '{ideia.descricao}': {product_url}")
#     registrar_evento(f"Novo produto '{ideia.descricao}' publicado na Gumroad: {product_url}", ed.locais) # Assuming ed.locais is accessible
#
#     # >> Integration point for Divulgador <<
#     from .divulgador import sugerir_conteudo_marketing # Import Divulgador function
#     sugestoes_marketing = sugerir_conteudo_marketing(ideia, product_url)
#     if sugestoes_marketing:
#         # Marketing suggestions are logged by an event within sugerir_conteudo_marketing
#         # Optionally, save them or process them further here.
#         logger.info(f"Conteúdo de marketing sugerido para {ideia.descricao} foi gerado.")
#     else:
#         logger.warning(f"Não foram geradas sugestões de marketing para {ideia.descricao}.")
#
# else:
#     logger.error(f"Falha ao criar produto digital para a ideia: {ideia.descricao}")
#     registrar_evento(f"Falha na criação do produto para ideia: {ideia.descricao}", ed.locais)


def sugerir_conteudo_marketing(ideia: Ideia, produto_link: str) -> Optional[str]:
    """
    Gera sugestões de conteúdo de marketing para um produto digital.

    Args:
        ideia: O objeto Ideia original.
        produto_link: O link público do produto (ex: Gumroad).

    Returns:
        Uma string contendo as sugestões de marketing em Markdown, ou None se falhar.
    """
    logger.info(f"Iniciando geração de sugestões de marketing para: {ideia.descricao}")

    # 1. LLM Model Selection
    try:
        selected_llm_model = selecionar_modelo(
            agent_type="Divulgador",
            objective="Gerar sugestões de conteúdo de marketing para um produto digital"
        )
        if not selected_llm_model:
            logger.error("Não foi possível selecionar um modelo LLM para o Divulgador.")
            # registrar_evento is not directly available unless passed or imported globally from ed
            # For now, just log. If this module becomes a full agent, it would have access.
            # ed.registrar_evento("Falha ao selecionar modelo LLM para Divulgador")
            return None
        logger.info(f"Modelo LLM selecionado para Divulgador: {selected_llm_model}")
    except Exception as e:
        logger.error(f"Erro ao selecionar modelo LLM para Divulgador: {e}")
        return None

    # 2. Marketing Content Prompt
    prompt_marketing = f"""Você é um Copywriter especialista em marketing digital e lançamentos de produtos.
Sua tarefa é criar sugestões de conteúdo de marketing para divulgar o seguinte produto digital:

Nome/Ideia do Produto: "{ideia.descricao}"
Justificativa/Breve Descrição: "{ideia.justificativa}"
Link para o Produto: {produto_link}

Crie o seguinte conteúdo de marketing:
1.  Dois (2) exemplos de posts curtos e chamativos para Twitter/X (máximo 280 caracteres cada).
2.  Um (1) post um pouco mais elaborado para LinkedIn, destacando os benefícios e o público-alvo.
3.  Um (1) pequeno texto (snippet) para um email marketing de anúncio do produto.

Instruções de Formato:
- A saída DEVE ser inteiramente em formato Markdown.
- Separe claramente cada sugestão de conteúdo (ex: "### Post para Twitter/X 1", "### Post para LinkedIn", etc.).
- Use técnicas de copywriting para tornar o conteúdo persuasivo e atraente.
- Inclua emojis relevantes onde apropriado para aumentar o engajamento.
- Certifique-se de que o link do produto seja incluído ou referenciado de forma natural nas sugestões.

Gere as sugestões de conteúdo de marketing agora.
"""
    logger.debug(f"Prompt para LLM (Divulgador - Marketing):\n{prompt_marketing}")

    # 3. LLM Call
    resposta_llm_marketing = None
    try:
        temp_agent = Agente(
            nome="DivulgadorAgenteMarketing",
            funcao="Divulgador", # Função genérica para o agente temporário
            modelo_llm=selected_llm_model
        )

        raw_response = chamar_openrouter_api(temp_agent, prompt_marketing)

        # Basic parsing, similar to criador_de_produtos.py
        if isinstance(raw_response, str):
            resposta_llm_marketing = raw_response
        elif hasattr(raw_response, 'text') and isinstance(raw_response.text, str):
            resposta_llm_marketing = raw_response.text
        elif isinstance(raw_response, dict) and 'choices' in raw_response and raw_response['choices']:
             choice = raw_response['choices'][0]
             if 'text' in choice: # Some models might use 'text' directly in choice
                 resposta_llm_marketing = choice['text']
             elif 'message' in choice and 'content' in choice['message']: # Standard OpenAI structure
                 resposta_llm_marketing = choice['message']['content']

        if not resposta_llm_marketing or not resposta_llm_marketing.strip():
            logger.error("LLM não retornou conteúdo de marketing.")
            # ed.registrar_evento(f"Falha na geração de marketing para '{ideia.descricao}': LLM retornou vazio.")
            return None

        logger.info(f"Sugestões de marketing geradas com sucesso para '{ideia.descricao}'.")
        # logger.debug(f"Sugestões de Marketing (raw):\n{resposta_llm_marketing}")

    except Exception as e:
        logger.error(f"Erro ao chamar LLM para sugestões de marketing: {e}", exc_info=True)
        # ed.registrar_evento(f"Exceção ao gerar marketing para '{ideia.descricao}': {e}")
        return None

    # 4. Logging Suggestions (registrar_evento from empresa_digital)
    # Assuming registrar_evento is available globally via `from state import registrar_evento` or use `state.registrar_evento`
    try:
        state.registrar_evento(f"Geradas sugestões de marketing para o produto: {ideia.descricao}. Link: {produto_link}")
        # Log the actual suggestions for more detail if needed, but might be too verbose for general event log
        # For detailed logging, use the module's logger:
        logger.info(f"Sugestões de marketing para '{ideia.descricao}':\n{resposta_llm_marketing}")
    except Exception as e:
        logger.error(f"Erro ao tentar registrar evento para sugestões de marketing: {e}")


    return resposta_llm_marketing


if __name__ == '__main__':
    # Setup basic logging for testing
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Teste do módulo divulgador.py")

    # Mock Ideia (assuming Ideia structure from ciclo_criativo.py)
    # No need to import the real Ideia if we define a compatible structure for testing
    class MockIdeiaForDivulgador:
        def __init__(self, descricao, justificativa):
            self.descricao = descricao
            self.justificativa = justificativa
            # Add other fields if sugerir_conteudo_marketing uses them, currently not.
            # self.link_produto = None

    # --- Mocking dependencies ---
    # Store original functions to restore them later
    original_selecionar_modelo = selecionar_modelo
    original_chamar_openrouter_api = chamar_openrouter_api
    # original_registrar_evento = registrar_evento # registrar_evento is now state.registrar_evento
    # Mocking state.registrar_evento in __main__ is more complex.

    def mock_selecionar_modelo_div(agent_type, objective):
        logger.info(f"Selecionando modelo (mock) para Divulgador: {agent_type} com objetivo '{objective}'")
        return "mock/gpt-3.5-turbo-creative" # Example model for Divulgador

    def mock_chamar_openrouter_api_div(agente, prompt):
        logger.info(f"Chamando OpenRouter API (mock) para Divulgador com agente {agente.nome} (modelo {agente.modelo_llm})")
        # Simulate LLM response for marketing content
        mock_marketing_output = f"""### Post para Twitter/X 1
        🚀 Lançamento! Nosso novo "{agente.funcao} - {ideia_teste_div.descricao}" está aqui para revolucionar! ✨ Confira e transforme seu dia: {produto_link_teste} #Novidade #Produtividade

        ### Post para Twitter/X 2
        Cansado de [problema que a ideia resolve]? 🤔 Descubra a solução com "{ideia_teste_div.descricao}"! Disponível agora: {produto_link_teste} #Solução #Inovação

        ### Post para LinkedIn
        **Apresentamos: {ideia_teste_div.descricao} – A Ferramenta Definitiva para [Público-Alvo]**

        Em um mundo onde [contexto do problema], encontrar soluções eficazes como "{ideia_teste_div.justificativa}" é crucial. É por isso que desenvolvemos "{ideia_teste_div.descricao}", um recurso poderoso para ajudar [Público-Alvo Específico] a alcançar [Benefício Principal].

        Com {ideia_teste_div.descricao}, você poderá:
        ✅ [Benefício 1]
        ✅ [Benefício 2]
        ✅ [Benefício 3]

        Não perca mais tempo com [problema]. Transforme sua abordagem hoje mesmo!
        Saiba mais e adquira o seu aqui: {produto_link_teste}

        #MarketingDigital #Lançamento #Produtividade #Inovação #[HashtagRelevante]

        ### Email Marketing Snippet
        **Assunto: Novidade Imperdível: {ideia_teste_div.descricao} já Disponível!**

        Olá [Nome do Cliente],

        Temos o prazer de anunciar o lançamento do nosso mais novo produto digital: **{ideia_teste_div.descricao}**!

        Se você busca [solução para o problema da justificativa], este {tipo_produto_email} foi criado especialmente para você. Com ele, você vai [principal benefício].

        Descubra todos os detalhes e garanta o seu acesso imediato aqui:
        {produto_link_teste}

        Atenciosamente,
        A Equipe [Nome da Empresa Fictícia]
        """
        # Add some variables that would be in the prompt for the mock output
        tipo_produto_email = "guia exclusivo" # Example
        return mock_marketing_output

    def mock_registrar_evento_div(mensagem, *args, **kwargs): # Allow for locais if used
        logger.info(f"EVENTO REGISTRADO (Divulgador Mock): {mensagem}")

    # Apply mocks
    selecionar_modelo = mock_selecionar_modelo_div
    chamar_openrouter_api = mock_chamar_openrouter_api_div
    # Mocking state.registrar_evento for __main__ block:
    original_state_registrar_evento = state.registrar_evento
    state.registrar_evento = mock_registrar_evento_div

    # --- Test Case ---
    ideia_teste_div = MockIdeiaForDivulgador(
        descricao="Curso Online de Fotografia com Celular",
        justificativa="Permite que qualquer pessoa tire fotos incríveis usando apenas o smartphone."
    )
    produto_link_teste = "https://gum.co/fotocelularpro"

    logger.info(f"\n--- Testando sugerir_conteudo_marketing para: {ideia_teste_div.descricao} ---")

    sugestoes = sugerir_conteudo_marketing(ideia_teste_div, produto_link_teste)

    if sugestoes:
        logger.info("Teste sugerir_conteudo_marketing SUCESSO.")
        # print("\nSugestões Geradas (mock):\n", sugestoes) # Already logged by the function
    else:
        logger.error("Teste sugerir_conteudo_marketing FALHOU: Nenhuma sugestão retornada.")

    # --- Test Case: LLM Fails to select model ---
    def mock_selecionar_modelo_fail(agent_type, objective):
        logger.info(f"Selecionando modelo (mock) - SIMULANDO FALHA para Divulgador")
        return None

    selecionar_modelo = mock_selecionar_modelo_fail
    logger.info(f"\n--- Testando sugerir_conteudo_marketing com FALHA na seleção de modelo ---")
    sugestoes_fail_model = sugerir_conteudo_marketing(ideia_teste_div, produto_link_teste)
    if sugestoes_fail_model is None:
        logger.info("Teste de falha na seleção de modelo SUCESSO: Nenhuma sugestão retornada, como esperado.")
    else:
        logger.error("Teste de falha na seleção de modelo FALHOU.")

    # --- Test Case: LLM Call Fails ---
    selecionar_modelo = mock_selecionar_modelo_div # Restore working model selection
    def mock_chamar_openrouter_api_fail(agente, prompt):
        logger.info(f"Chamando OpenRouter API (mock) - SIMULANDO FALHA para Divulgador")
        raise Exception("Simulated LLM API call failure")

    chamar_openrouter_api = mock_chamar_openrouter_api_fail
    logger.info(f"\n--- Testando sugerir_conteudo_marketing com FALHA na chamada da API LLM ---")
    sugestoes_fail_api = sugerir_conteudo_marketing(ideia_teste_div, produto_link_teste)
    if sugestoes_fail_api is None:
        logger.info("Teste de falha na API LLM SUCESSO: Nenhuma sugestão retornada, como esperado.")
    else:
        logger.error("Teste de falha na API LLM FALHOU.")

    # Restore original functions
    selecionar_modelo = original_selecionar_modelo
    chamar_openrouter_api = original_chamar_openrouter_api
    state.registrar_evento = original_state_registrar_evento # Restore

    logger.info("\nTestes do módulo divulgador.py concluídos.")

# Note: To make `registrar_evento` directly usable without `ed.` prefix,
# it would need to be imported like `from .empresa_digital import registrar_evento`.
# The current implementation assumes it's available in the global scope if this module
# were part of a larger system where `empresa_digital` functions are globally accessible
# or if `divulgador.py` itself becomes an agent within `empresa_digital.py`.
# For the standalone function `sugerir_conteudo_marketing`, if it needs `registrar_evento`,
# it should ideally be passed as an argument or the module needs to import it directly.
# The current version imports it.
