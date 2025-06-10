import logging
import os
import json # May be needed for LLM response parsing, or direct string manipulation
import re # For sanitizing filenames

# Relative imports
from .empresa_digital import Ideia, registrar_evento, Agente # Assuming Agente can be imported directly
from .openrouter_utils import selecionar_modelo, chamar_openrouter_api
from .gumroad import create_product, get_gumroad_api_key

# Module-level logger
logger = logging.getLogger(__name__)

# Directory for generated products
PRODUTOS_GERADOS_DIR = "produtos_gerados"

def produto_digital(ideia: Ideia, empresa_agentes: dict, todos_locais: dict):
    """
    Generates a digital product based on an Ideia, saves it, and publishes it to Gumroad.

    Args:
        ideia: An Ideia object.
        empresa_agentes: The agentes dictionary from empresa_digital.py. (Used for context, if needed)
        todos_locais: The locais dictionary from empresa_digital.py. (Used for context, if needed)

    Returns:
        The Gumroad URL of the published product, or None if any step fails.
    """
    logger.info(f"Iniciando criação de produto digital para a ideia: {ideia.descricao}")

    # Ensure the directory for generated products exists
    try:
        os.makedirs(PRODUTOS_GERADOS_DIR, exist_ok=True)
        logger.info(f"Diretório '{PRODUTOS_GERADOS_DIR}' assegurado.")
    except OSError as e:
        logger.error(f"Erro ao criar diretório '{PRODUTOS_GERADOS_DIR}': {e}")
        registrar_evento(f"Falha ao criar diretório de produtos: {e}", locals()) # Assuming registrar_evento can be called
        return None

    # 1. LLM Model Selection
    try:
        # TODO: Confirm if 'empresa_agentes' or 'todos_locais' is needed for selecionar_modelo context
        # For now, assuming it might take a simple string for agent_type or role
        selected_llm_model = selecionar_modelo(agent_type="CriadorDeProdutos", objective="Gerar conteúdo de produto digital vendável")
        if not selected_llm_model:
            logger.error("Não foi possível selecionar um modelo LLM para a criação de produtos.")
            registrar_evento("Falha ao selecionar modelo LLM para CriadorDeProdutos", locals())
            return None
        logger.info(f"Modelo LLM selecionado para CriadorDeProdutos: {selected_llm_model}")
    except Exception as e:
        logger.error(f"Erro ao selecionar modelo LLM: {e}")
        registrar_evento(f"Exceção ao selecionar modelo LLM: {e}", locals())
        return None

    # 2. Content Generation Prompt
    # tipo_produto could be dynamic or chosen based on ideia.complexidade perhaps
    tipo_produto = "guia prático conciso"
    prompt_content_generation = f"""Você é um especialista em criar produtos digitais de alta qualidade e valor.
Sua tarefa é criar o conteúdo completo para um {tipo_produto} baseado na seguinte ideia:
Descrição da Ideia: "{ideia.descricao}"
Justificativa da Ideia: "{ideia.justificativa}"

O conteúdo deve ser:
- Extremamente útil e prático para o público-alvo.
- Bem estruturado e fácil de ler.
- Pronto para ser vendido como um produto digital independente.
- Original e não uma simples reformulação de conteúdo existente.

Instruções de formato:
- A saída DEVE ser inteiramente em formato Markdown.
- Comece com um título principal (H1).
- Divida o conteúdo em seções lógicas usando subtítulos (H2, H3).
- Use listas, negrito, itálico e outros elementos Markdown para melhorar a legibilidade.
- Se aplicável, inclua exemplos práticos, checklists ou templates.
- O tom deve ser profissional, mas acessível.

Gere o conteúdo completo do {tipo_produto} agora.
"""
    logger.debug(f"Prompt para LLM (geração de conteúdo):\n{prompt_content_generation}")

    # 3. LLM Call
    resposta_llm_content = None
    try:
        # Instantiate a temporary Agente for the API call
        temp_agent = Agente(nome="CriadorDeProdutosAgente", funcao="CriadorDeProdutos", modelo_llm=selected_llm_model)

        # Assuming chamar_openrouter_api takes agent object and prompt string
        # And returns the text content directly or a structure with it.
        # Let's assume it returns a string or an object with a 'text' attribute.
        raw_response = chamar_openrouter_api(temp_agent, prompt_content_generation) # TODO: Check exact return type

        if isinstance(raw_response, str):
            resposta_llm_content = raw_response
        elif hasattr(raw_response, 'text') and isinstance(raw_response.text, str): # Common pattern for response objects
            resposta_llm_content = raw_response.text
        elif isinstance(raw_response, dict) and 'choices' in raw_response and raw_response['choices']: # OpenAI like structure
             if 'text' in raw_response['choices'][0]:
                 resposta_llm_content = raw_response['choices'][0]['text']
             elif 'message' in raw_response['choices'][0] and 'content' in raw_response['choices'][0]['message']:
                 resposta_llm_content = raw_response['choices'][0]['message']['content']


        if not resposta_llm_content or not resposta_llm_content.strip():
            logger.error("LLM não retornou conteúdo para o produto.")
            registrar_evento("Falha na geração de conteúdo: LLM retornou vazio.", locals())
            return None
        logger.info("Conteúdo do produto gerado pelo LLM com sucesso.")
        # logger.debug(f"Conteúdo gerado (primeiros 300 chars):\n{resposta_llm_content[:300]}")

    except Exception as e:
        logger.error(f"Erro ao chamar LLM para geração de conteúdo: {e}")
        registrar_evento(f"Exceção ao chamar LLM para conteúdo: {e}", locals())
        return None

    # 4. Saving Content
    try:
        # Sanitize ideia.descricao for filename
        # Remove non-alphanumeric characters (except spaces, which become underscores) and limit length
        sanitized_description = re.sub(r'[^\w\s-]', '', ideia.descricao.lower())
        sanitized_description = re.sub(r'[-\s]+', '_', sanitized_description).strip('_')
        filename_base = sanitized_description[:50] if sanitized_description else "produto_sem_titulo"

        product_filename = f"{filename_base}.md"
        product_filepath = os.path.join(PRODUTOS_GERADOS_DIR, product_filename)

        with open(product_filepath, "w", encoding="utf-8") as f:
            f.write(resposta_llm_content)
        logger.info(f"Conteúdo do produto salvo em: {product_filepath}")

    except Exception as e:
        logger.error(f"Erro ao salvar conteúdo do produto: {e}")
        registrar_evento(f"Exceção ao salvar arquivo do produto: {e}", locals())
        return None

    # 5. Gumroad Publishing
    gumroad_api_key = None
    try:
        gumroad_api_key = get_gumroad_api_key()
        logger.info("Chave da API Gumroad obtida com sucesso.")
    except ValueError as e:
        logger.error(f"Erro ao obter chave da API Gumroad: {e}")
        registrar_evento(f"Falha ao obter chave Gumroad: {e}", locals())
        # Cleanup local file if we can't even attempt to publish
        if os.path.exists(product_filepath):
            try:
                os.remove(product_filepath)
                logger.info(f"Arquivo local '{product_filepath}' removido devido à falha na obtenção da chave da API.")
            except OSError as ose:
                logger.error(f"Erro ao remover arquivo local '{product_filepath}': {ose}")
        return None

    product_url = None
    try:
        # Determine description for Gumroad: use justificativa or a snippet of content
        gumroad_description = ideia.justificativa
        if not gumroad_description and resposta_llm_content:
            # Create a short snippet from the beginning of the content
            # Remove Markdown headings for a cleaner snippet
            plain_content_snippet = re.sub(r'#+\s*', '', resposta_llm_content[:500])
            gumroad_description = plain_content_snippet.split('\n\n')[0] # First paragraph

        logger.info(f"Tentando publicar produto '{ideia.descricao}' na Gumroad.")
        product_url = create_product(
            name=ideia.descricao,
            price_in_cents=500,  # Example: $5.00
            description=gumroad_description,
            file_path=product_filepath, # Path to the saved .md file
            currency="USD"
        )

        if product_url:
            logger.info(f"Produto '{ideia.descricao}' publicado com sucesso na Gumroad: {product_url}")
            registrar_evento(f"Novo produto '{ideia.descricao}' criado e publicado na Gumroad: {product_url}", todos_locais) # Pass todos_locais
            return product_url
        else:
            # This case should ideally be caught by exceptions in create_product if it's robust
            logger.error("Falha ao criar produto na Gumroad (create_product retornou None ou similar).")
            registrar_evento(f"Falha ao publicar '{ideia.descricao}' na Gumroad (retorno None).", todos_locais)
            # Fall through to cleanup

    except Exception as e: # Catch exceptions from create_product (e.g., API errors, file errors)
        logger.error(f"Erro ao publicar produto na Gumroad: {e}")
        registrar_evento(f"Exceção ao publicar '{ideia.descricao}' na Gumroad: {e}", todos_locais)
        # Fall through to cleanup

    # Cleanup if Gumroad publishing failed
    if not product_url and os.path.exists(product_filepath):
        try:
            os.remove(product_filepath)
            logger.info(f"Arquivo local '{product_filepath}' removido devido à falha na publicação na Gumroad.")
        except OSError as e:
            logger.error(f"Erro ao remover arquivo local '{product_filepath}' após falha na publicação: {e}")

    return None


if __name__ == '__main__':
    # Setup basic logging for testing
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Teste do módulo criador_de_produtos.py")

    # Mocking Ideia and other dependencies for local testing
    class MockIdeia(Ideia):
        def __init__(self, descricao, justificativa, complexidade=1, potencial_lucro=1, prioridade=1, validada=False):
            super().__init__(descricao, justificativa, complexidade, potencial_lucro, prioridade)
            self.validada = validada

    # Mock registrar_evento
    def mock_registrar_evento(mensagem, locais_usados):
        logger.info(f"EVENTO REGISTRADO (mock): {mensagem} (Locais: {list(locais_usados.keys()) if isinstance(locais_usados, dict) else locais_usados})")

    # Replace actual registrar_evento with mock for local test
    global registrar_evento
    original_registrar_evento = registrar_evento
    registrar_evento = mock_registrar_evento

    # Mock selecionar_modelo
    original_selecionar_modelo = selecionar_modelo
    def mock_selecionar_modelo(agent_type, objective):
        logger.info(f"Selecionando modelo (mock) para {agent_type} com objetivo '{objective}'")
        # return "mistral/mistral-medium" # Example model
        return "openai/gpt-3.5-turbo" # A common, usually available model
    global selecionar_modelo
    selecionar_modelo = mock_selecionar_modelo

    # Mock chamar_openrouter_api
    original_chamar_openrouter_api = chamar_openrouter_api
    def mock_chamar_openrouter_api(agente, prompt):
        logger.info(f"Chamando OpenRouter API (mock) com agente {agente.nome} (modelo {agente.modelo_llm})")
        # logger.debug(f"Prompt para LLM (mock):\n{prompt}")
        # Simulate LLM response
        return f"# Guia Incrível sobre {agente.nome}\n\nEste é um guia gerado pelo mock LLM para testar o fluxo.\n\n## Seção 1\nConteúdo da seção 1.\n\n## Seção 2\nChecklist:\n- [ ] Item 1\n- [ ] Item 2"
    global chamar_openrouter_api
    chamar_openrouter_api = mock_chamar_openrouter_api

    # Mock get_gumroad_api_key
    original_get_gumroad_api_key = get_gumroad_api_key
    def mock_get_gumroad_api_key():
        logger.info("Obtendo chave da API Gumroad (mock)")
        # Simulate key found. To test failure, raise ValueError("Mock Gumroad API key not found")
        # return "MOCK_GUMROAD_API_KEY_SUCCESS"
        # Simulate key not found for specific test case:
        if os.environ.get("TEST_GUMROAD_KEY_FAILURE"):
            raise ValueError("Mock Gumroad API key not found (simulated failure)")
        return "MOCK_GUMROAD_API_KEY_SUCCESS"
    global get_gumroad_api_key
    get_gumroad_api_key = mock_get_gumroad_api_key

    # Mock create_product
    original_create_product = create_product
    def mock_create_product(name, price_in_cents, description, file_path, currency):
        logger.info(f"Criando produto na Gumroad (mock): {name}, Preço: {price_in_cents} {currency}")
        logger.info(f"  Descrição (mock): {description}")
        logger.info(f"  Caminho do arquivo (mock): {file_path}")
        if not os.path.exists(file_path):
             logger.error(f"  Arquivo {file_path} não encontrado para mock_create_product!")
             raise FileNotFoundError(f"Mock: Arquivo {file_path} não encontrado.")
        # Simulate success:
        # return f"https://gum.co/mock_{name.replace(' ', '_')[:10]}"
        # Simulate failure:
        if os.environ.get("TEST_GUMROAD_PUBLISH_FAILURE"):
             logger.warning("Simulando falha na publicação Gumroad (mock).")
             return None # Or raise an exception like requests.exceptions.HTTPError("Mock Gumroad API error")
        return f"https://gum.co/mock_{name.replace(' ', '_')[:10]}"

    global create_product
    create_product = mock_create_product

    # Test case 1: Successful product creation
    logger.info("\n--- Iniciando Teste 1: Criação de produto com sucesso ---")
    ideia_teste_1 = MockIdeia(
        descricao="Guia Completo de Jardinagem Urbana para Iniciantes",
        justificativa="Muitas pessoas em cidades querem começar a jardinar mas não sabem como."
    )
    mock_empresa_agentes = {} # Not used by current produto_digital structure directly
    mock_todos_locais = {"global": "contexto_global"} # For registrar_evento

    url_produto_1 = produto_digital(ideia_teste_1, mock_empresa_agentes, mock_todos_locais)
    if url_produto_1:
        logger.info(f"Teste 1 SUCESSO: URL do produto: {url_produto_1}")
        # Verify file exists (it should, as mock_create_product doesn't clean it up on its own)
        expected_filename = "guia_completo_de_jardinagem_urbana_para_iniciant.md" # first 50 chars of sanitized name
        expected_filepath = os.path.join(PRODUTOS_GERADOS_DIR, expected_filename)
        if os.path.exists(expected_filepath):
            logger.info(f"Arquivo {expected_filepath} encontrado como esperado.")
            # Clean up the file created by the successful test run
            try:
                os.remove(expected_filepath)
                logger.info(f"Arquivo de teste {expected_filepath} removido.")
            except OSError as e:
                logger.error(f"Erro ao remover arquivo de teste {expected_filepath}: {e}")
        else:
            logger.error(f"Arquivo {expected_filepath} NÃO encontrado após Teste 1.")

    else:
        logger.error("Teste 1 FALHOU: Produto não foi criado.")

    # Test case 2: Gumroad API key not found
    logger.info("\n--- Iniciando Teste 2: Falha ao obter chave Gumroad ---")
    os.environ["TEST_GUMROAD_KEY_FAILURE"] = "true"
    ideia_teste_2 = MockIdeia(
        descricao="Ebook de Receitas Veganas Rápidas",
        justificativa="Pessoas buscam refeições veganas fáceis e rápidas para o dia a dia."
    )
    url_produto_2 = produto_digital(ideia_teste_2, mock_empresa_agentes, mock_todos_locais)
    if url_produto_2 is None:
        logger.info("Teste 2 SUCESSO: Produto não criado devido à ausência de chave API, como esperado.")
        # Verify file was cleaned up
        expected_filename_2 = "ebook_de_receitas_veganas_rapidas.md"
        expected_filepath_2 = os.path.join(PRODUTOS_GERADOS_DIR, expected_filename_2)
        if not os.path.exists(expected_filepath_2):
            logger.info(f"Arquivo {expected_filepath_2} não encontrado, limpeza funcionou.")
        else:
            logger.error(f"Arquivo {expected_filepath_2} AINDA EXISTE após Teste 2, limpeza falhou.")
            os.remove(expected_filepath_2) # Manual cleanup
    else:
        logger.error(f"Teste 2 FALHOU: Produto foi criado ({url_produto_2}) mesmo com simulação de falha na API key.")
    del os.environ["TEST_GUMROAD_KEY_FAILURE"]

    # Test case 3: Gumroad publishing fails
    logger.info("\n--- Iniciando Teste 3: Falha na publicação na Gumroad ---")
    os.environ["TEST_GUMROAD_PUBLISH_FAILURE"] = "true"
    ideia_teste_3 = MockIdeia(
        descricao="Templates de Email Marketing para Pequenas Empresas",
        justificativa="Pequenas empresas precisam de ajuda para criar emails eficazes."
    )
    url_produto_3 = produto_digital(ideia_teste_3, mock_empresa_agentes, mock_todos_locais)
    if url_produto_3 is None:
        logger.info("Teste 3 SUCESSO: Produto não publicado na Gumroad e URL não retornada, como esperado.")
        # Verify file was cleaned up
        expected_filename_3 = "templates_de_email_marketing_para_pequenas_empres.md"
        expected_filepath_3 = os.path.join(PRODUTOS_GERADOS_DIR, expected_filename_3)
        if not os.path.exists(expected_filepath_3):
            logger.info(f"Arquivo {expected_filepath_3} não encontrado, limpeza funcionou.")
        else:
            logger.error(f"Arquivo {expected_filepath_3} AINDA EXISTE após Teste 3, limpeza falhou.")
            os.remove(expected_filepath_3) # Manual cleanup
    else:
        logger.error(f"Teste 3 FALHOU: Produto foi publicado ({url_produto_3}) mesmo com simulação de falha na Gumroad.")
    del os.environ["TEST_GUMROAD_PUBLISH_FAILURE"]

    # Restore original functions
    registrar_evento = original_registrar_evento
    selecionar_modelo = original_selecionar_modelo
    chamar_openrouter_api = original_chamar_openrouter_api
    get_gumroad_api_key = original_get_gumroad_api_key
    create_product = original_create_product

    logger.info("\nTestes do módulo criador_de_produtos.py concluídos.")
    # Cleanup PRODUTOS_GERADOS_DIR if empty and created by tests
    if os.path.exists(PRODUTOS_GERADOS_DIR) and not os.listdir(PRODUTOS_GERADOS_DIR):
        try:
            os.rmdir(PRODUTOS_GERADOS_DIR)
            logger.info(f"Diretório de teste '{PRODUTOS_GERADOS_DIR}' removido pois estava vazio.")
        except OSError as e:
            logger.warning(f"Não foi possível remover o diretório '{PRODUTOS_GERADOS_DIR}': {e}")

# Example of how it might be called from the main loop (conceptual)
# if __name__ == '__main_simulation__':
#     # Assuming 'ideia_atual' is an Ideia instance
#     # Assuming 'empresa_agentes_globais' and 'locais_globais' are available
#     # url_novo_produto = produto_digital(ideia_atual, empresa_agentes_globais, locais_globais)
#     # if url_novo_produto:
#     #     print(f"Produto criado: {url_novo_produto}")
#     # else:
#     #     print("Falha ao criar produto.")
#     pass
