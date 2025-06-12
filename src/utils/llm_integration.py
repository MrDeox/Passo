import os
import openai
from typing import Any, Dict, Optional
# from src.core.company_settings import CompanySettings # Para obter o provider e modelo padrão

class LLMIntegration:
    """
    Classe para abstrair a comunicação com diferentes provedores de LLM.
    """
    def __init__(self, settings: Any): # Deveria ser CompanySettings ou similar
        self.settings = settings
        self.llm_provider = settings.llm_provider
        self.default_model = settings.default_llm_model
        self.api_key: Optional[str] = None
        self.openai_client: Optional[openai.AsyncOpenAI] = None

        self._load_api_key()
        if self.api_key:
            self.openai_client = openai.AsyncOpenAI(api_key=self.api_key)

        print(f"[LLMIntegration] Inicializado com provider '{self.llm_provider}' e modelo padrão '{self.default_model}'.")

    def _load_api_key(self):
        """
        Carrega a API key do OpenAI a partir das configurações.
        """
        try:
            self.api_key = self.settings.openai_api_key
            if not self.api_key:
                print(f"[LLMIntegration] ALERTA: OpenAI API Key não encontrada nas configurações (settings.openai_api_key está vazia).")
                self.api_key = None
            # else:
            #     print(f"[LLMIntegration] OpenAI API Key carregada com sucesso.") # Opcional: log de sucesso
        except AttributeError:
            print(f"[LLMIntegration] ALERTA: Atributo 'openai_api_key' não encontrado em settings. Verifique a configuração de CompanySettings.")
            self.api_key = None
        except Exception as e:
            print(f"[LLMIntegration] Erro ao carregar OpenAI API Key: {e}")
            self.api_key = None

    async def generate_text(self, prompt: str, model_name: Optional[str] = None, params: Optional[Dict] = None) -> str:
        """
        Gera texto usando o LLM configurado.
        """
        target_model = model_name or self.default_model
        request_params = params or {}

        print(f"[LLMIntegration] Enviando prompt para {self.llm_provider} (modelo {target_model}): {prompt[:100]}...")

        if self.llm_provider == "openai":
            if not self.openai_client:
                print("[LLMIntegration] ALERTA: Cliente OpenAI não inicializado. Verifique a API Key.")
                return "Erro: Cliente OpenAI não configurado."

            try:
                response = await self.openai_client.chat.completions.create(
                    model=target_model,
                    messages=[{"role": "user", "content": prompt}],
                    **request_params
                )
                return response.choices[0].message.content.strip()
            except openai.APIError as e:
                print(f"[LLMIntegration] Erro da API OpenAI: {e}")
                return f"Erro da API OpenAI: {e}"
            except Exception as e:
                print(f"[LLMIntegration] Erro inesperado ao chamar a API OpenAI: {e}")
                return f"Erro inesperado ao chamar a API OpenAI: {e}"

        elif self.llm_provider == "openrouter":
            # Manter lógica para outros providers, se houver
            print(f"[LLMIntegration] Provider 'openrouter' encontrado, mas a lógica de chamada não está implementada nesta atualização.")
            return f"Resposta simulada do OpenRouter para: {prompt[:50]}"
        else: # default_provider ou não implementado
            print(f"[LLMIntegration] Provider '{self.llm_provider}' não implementado ou desconhecido. Retornando resposta mockada.")
            return f"Resposta mockada (provider {self.llm_provider} não configurado): {prompt[:50]}"

    # Poderiam existir métodos mais específicos, como generate_json_output, etc.
