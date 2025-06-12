import pytest
from unittest.mock import patch, MagicMock

# Assuming divulgador.py and other modules are in the parent directory
# or accessible via PYTHONPATH
from divulgador import sugerir_conteudo_marketing
from core_types import Ideia # For type hinting and creating test Ideia
# from empresa_digital import Agente # Agente is used internally by divulgador.py

@pytest.fixture
def sample_ideia_for_divulgador():
    # Using the actual Ideia class if its definition is simple and stable
    return Ideia(
        descricao="Guia Completo de Marketing Digital",
        justificativa="Ajuda pequenas empresas a decolar online.",
        autor="Guru do Marketing"
        # link_produto would be set before calling sugerir_conteudo_marketing
    )

@pytest.fixture
def mock_divulgador_dependencies():
    with patch('divulgador.selecionar_modelo') as mock_select_model, \
         patch('divulgador.chamar_openrouter_api') as mock_call_llm, \
         patch('divulgador.state.registrar_evento') as mock_register_event: # Patched state.registrar_evento

        yield {
            "select_model": mock_select_model,
            "call_llm": mock_call_llm,
            "register_event": mock_register_event,
        }

class TestSugerirConteudoMarketing:

    def test_successful_marketing_suggestion(self, sample_ideia_for_divulgador, mock_divulgador_dependencies):
        mock_divulgador_dependencies["select_model"].return_value = "mock_marketing_model"
        expected_suggestions = "### Post para Twitter\nCompre nosso produto!\n### Email\nSuper oferta!"
        mock_divulgador_dependencies["call_llm"].return_value = expected_suggestions

        product_link = "https://gum.co/marketing_guide"

        result = sugerir_conteudo_marketing(sample_ideia_for_divulgador, product_link)

        assert result == expected_suggestions
        mock_divulgador_dependencies["select_model"].assert_called_once_with(
            agent_type="Divulgador",
            objective="Gerar sugestões de conteúdo de marketing para um produto digital"
        )
        mock_divulgador_dependencies["call_llm"].assert_called_once()
        # registrar_evento is called with the product description and link
        mock_divulgador_dependencies["register_event"].assert_called_once_with(
            f"Geradas sugestões de marketing para o produto: {sample_ideia_for_divulgador.descricao}. Link: {product_link}"
        )
        # Logger.info is also called, can be checked with caplog if needed

    def test_llm_model_selection_fails(self, sample_ideia_for_divulgador, mock_divulgador_dependencies):
        mock_divulgador_dependencies["select_model"].return_value = None
        product_link = "https://gum.co/some_product"

        result = sugerir_conteudo_marketing(sample_ideia_for_divulgador, product_link)

        assert result is None
        mock_divulgador_dependencies["call_llm"].assert_not_called()
        mock_divulgador_dependencies["register_event"].assert_not_called() # Event only on success

    def test_llm_call_returns_empty_content(self, sample_ideia_for_divulgador, mock_divulgador_dependencies):
        mock_divulgador_dependencies["select_model"].return_value = "mock_marketing_model"
        mock_divulgador_dependencies["call_llm"].return_value = "" # Empty or whitespace-only
        product_link = "https://gum.co/another_product"

        result = sugerir_conteudo_marketing(sample_ideia_for_divulgador, product_link)

        assert result is None
        mock_divulgador_dependencies["register_event"].assert_not_called()

    def test_llm_call_api_error(self, sample_ideia_for_divulgador, mock_divulgador_dependencies):
        mock_divulgador_dependencies["select_model"].return_value = "mock_marketing_model"
        mock_divulgador_dependencies["call_llm"].side_effect = Exception("LLM API connection failed")
        product_link = "https://gum.co/error_product"

        result = sugerir_conteudo_marketing(sample_ideia_for_divulgador, product_link)

        assert result is None
        mock_divulgador_dependencies["register_event"].assert_not_called()

    def test_llm_response_parsing_various_formats(self, sample_ideia_for_divulgador, mock_divulgador_dependencies):
        mock_divulgador_dependencies["select_model"].return_value = "mock_model"
        product_link = "https://gum.co/parsing_test"

        # Test 1: Direct string (already tested in success case)

        # Test 2: Object with .text attribute
        mock_response_obj = MagicMock()
        mock_response_obj.text = "Response from .text attribute"
        mock_divulgador_dependencies["call_llm"].return_value = mock_response_obj
        result = sugerir_conteudo_marketing(sample_ideia_for_divulgador, product_link)
        assert result == "Response from .text attribute"
        mock_divulgador_dependencies["register_event"].assert_called_with(
            f"Geradas sugestões de marketing para o produto: {sample_ideia_for_divulgador.descricao}. Link: {product_link}"
        )
        mock_divulgador_dependencies["register_event"].reset_mock() # Reset for next call

        # Test 3: OpenAI-like dictionary structure (message.content)
        openai_response = {
            "choices": [
                {
                    "message": {
                        "content": "Response from message.content"
                    }
                }
            ]
        }
        mock_divulgador_dependencies["call_llm"].return_value = openai_response
        result = sugerir_conteudo_marketing(sample_ideia_for_divulgador, product_link)
        assert result == "Response from message.content"
        mock_divulgador_dependencies["register_event"].assert_called_with(
            f"Geradas sugestões de marketing para o produto: {sample_ideia_for_divulgador.descricao}. Link: {product_link}"
        )
        mock_divulgador_dependencies["register_event"].reset_mock()

        # Test 4: OpenAI-like dictionary structure (choice.text) - older models
        openai_text_response = {
            "choices": [
                {
                    "text": "Response from choice.text"
                }
            ]
        }
        mock_divulgador_dependencies["call_llm"].return_value = openai_text_response
        result = sugerir_conteudo_marketing(sample_ideia_for_divulgador, product_link)
        assert result == "Response from choice.text"
        mock_divulgador_dependencies["register_event"].assert_called_with(
            f"Geradas sugestões de marketing para o produto: {sample_ideia_for_divulgador.descricao}. Link: {product_link}"
        )


# To run: PYTHONPATH=. pytest tests/test_divulgador.py
# Ensure ciclo_criativo.py (for Ideia) is in the PYTHONPATH.
# divulgador.py imports Agente from .empresa_digital, which is fine for the temp agent instantiation.
# registrar_evento is also imported from .empresa_digital.
