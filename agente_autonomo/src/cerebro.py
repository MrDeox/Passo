import os
import requests
from dotenv import load_dotenv
from .utils import setup_logger

load_dotenv()

class CerebroExterno:
    def __init__(self, api_url: str = 'https://openrouter.ai/api/v1/chat/completions',
                 model: str = 'deepseek/deepseek-chat-v3-0324:free'):
        """Inicializa o CerebroExterno.

        Parameters
        ----------
        api_url: str
            Endpoint da API do OpenRouter.
        model: str
            Modelo a ser utilizado nas chamadas.
        """
        self.api_url = api_url
        self.model = model
        self.logger = setup_logger('cerebro', 'cerebro.log')
        self.api_key = os.getenv('OPENROUTER_API_KEY', os.getenv('OPENAI_API_KEY', ''))

    def __init__(self, api_url: str = 'https://openrouter.ai/api/v1/chat/completions'):
        self.api_url = api_url
        self.logger = setup_logger('cerebro', 'cerebro.log')
        self.api_key = os.getenv('OPENAI_API_KEY', '')


    def gerar_resposta(self, prompt: str) -> str:
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        data = {

            'model': self.model,

            'model': 'openai/gpt-3.5-turbo',

            'messages': [
                {'role': 'user', 'content': prompt}
            ]
        }
        try:
            resp = requests.post(self.api_url, json=data, headers=headers, timeout=30)
            resp.raise_for_status()
            result = resp.json()
            message = result['choices'][0]['message']['content']
            self.logger.info('LLM resposta gerada')
            return message
        except Exception as e:
            self.logger.error(f'Erro ao chamar LLM: {e}')
            return ''
