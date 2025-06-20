import os
import ast
import asyncio
import json
import sys
import base64
import subprocess
import logging
import glob
import re
from datetime import datetime
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Configuração do logger
def setup_logger(name, log_file='agente_hifen.log', level=logging.INFO):
    # Cria diretório para logs históricos
    os.makedirs("backup_logs", exist_ok=True)
    
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    handler = logging.FileHandler(log_file)
    handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger = logging.getLogger(name)
    logger.setLevel(level)
    logger.addHandler(handler)
    logger.addHandler(console_handler)
    
    return logger

class CerebroExterno:
    def __init__(self):
        load_dotenv()
        self.client = AsyncOpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.getenv("OPENROUTER_API_KEY")
        )
        self.logger = logging.getLogger('CerebroExterno')
    
    async def gerar_hipotese(self, codigo_fonte: str, log_execucao: str) -> str:
        self.logger.debug("Iniciando chamada ao LLM...")
        
        try:
            response = await self.client.chat.completions.create(
                model="deepseek/deepseek-r1-0528:free",
                messages=[{
                    "role": "user",
                    "content": f"""CONTEXTO: Eu sou um agente de IA autônomo. Abaixo estão meu código-fonte atual e o log completo da minha última tentativa de execução.

[MEU CÓDIGO-FONTE ATUAL]
{codigo_fonte}

[LOG DA EXECUÇÃO ANTERIOR]
{log_execucao}

TAREFA:
1.  **DIAGNÓSTICO:** Analise o 'LOG DA EXECUÇÃO ANTERIOR'.
2.  **AÇÃO:**
    -   **SE o log contém um 'ModuleNotFoundError'**: Sua ÚNICA tarefa é identificar o nome do módulo que falta. Responda APENAS com o nome do pacote em formato JSON. Exemplo: {{"acao": "instalar", "pacote": "spacy"}}.
    -   **SE o log contém qualquer outro erro (Traceback)**: Sua tarefa é corrigir o bug no meu código-fonte. Responda com o código-fonte COMPLETO e MODIFICADO.
    -   **SE NÃO HOUVER ERROS:** Proponha uma única modificação que me otimize ou adicione uma nova funcionalidade. Responda com o código-fonte COMPLETO e MODIFICADO."""
                }],
                extra_headers={
                    "HTTP-Referer": "https://github.com/arthurprojects/Passo",
                    "X-Title": "AgentHifen Debugger"
                },
                stream=True
            )
            
            resposta_completa = ""
            self.logger.info("Streaming resposta do LLM:")
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    print(chunk.choices[0].delta.content, end='', flush=True)
                    resposta_completa += chunk.choices[0].delta.content
            
            self.logger.debug("Chamada ao LLM concluída")
            return resposta_completa
        except Exception as e:
            self.logger.error(f"Erro na chamada ao LLM: {str(e)}")
            return ""

class AgentHifen:
    def __init__(self, log_anterior: str = ""):
        self.logger = setup_logger('AgentHifen')
        self.cerebro = CerebroExterno()
        self.log_anterior = log_anterior
        self.logger.info("AgentHifen inicializado")
    
    def criar_backup(self, codigo: str) -> None:
        """Cria backup do código atual com timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_logs/backup_{timestamp}.py"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(codigo)
        self.logger.info(f"Backup criado: {backup_path}")

    def instalar_dependencia(self, nome_pacote: str) -> bool:
        self.logger.debug(f"Instalando dependência: {nome_pacote}")
        try:
            subprocess.run(
                [sys.executable, '-m', 'pip', 'install', nome_pacote],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.logger.info(f"Pacote {nome_pacote} instalado com sucesso!")
            return True
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Erro ao instalar {nome_pacote}: {e.stderr.decode()}")
            return False

    def ler_codigo_fonte(self) -> str:
        self.logger.debug("Lendo código fonte...")
        with open(__file__, 'r', encoding='utf-8') as f:
            return f.read()
    
    def limpar_hipotese(self, hipotese_bruta: str) -> str:
        self.logger.debug("Limpando hipótese...")
        # Remove qualquer texto antes do primeiro bloco de código
        start_idx = hipotese_bruta.find('```python')
        if start_idx == -1:
            start_idx = hipotese_bruta.find('```')
            if start_idx == -1:
                return hipotese_bruta.strip()
        
        start_idx = hipotese_bruta.find('\n', start_idx) + 1
        end_idx = hipotese_bruta.rfind('```')
        
        if start_idx > 0 and end_idx > 0:
            return hipotese_bruta[start_idx:end_idx].strip()
        return hipotese_bruta.strip()

    def validar_hipotese(self, codigo_hipotetico: str) -> bool:
        self.logger.debug("Validando hipótese...")
        try:
            ast.parse(codigo_hipotetico)
            self.logger.info("Validação bem-sucedida")
            return True
        except Exception as e:
            self.logger.error(f"Falha na validação: {e}")
            return False

    def aplicar_modificacao(self, codigo_atual: str, codigo_novo: str) -> None:
        self.logger.info("Aplicando modificação...")
        self.criar_backup(codigo_atual)  # Backup antes de modificar
        
        with open(__file__, 'w', encoding='utf-8') as f:
            f.write(codigo_novo)
        
        self.logger.info("Código atualizado com sucesso! Reiniciando o agente...")
        # Registra log de execução atual no histórico
        with open("agente_hifen.log", "r") as log_file:
            log_atual = log_file.read()
        log_b64 = base64.b64encode(log_atual.encode()).decode()
        subprocess.Popen([sys.executable, __file__, log_b64])
        exit(0)

    def restaurar_backup_recente(self) -> bool:
        """Restaura o backup mais recente em caso de falha crítica"""
        backups = glob.glob("backup_logs/backup_*.py")
        if not backups:
            return False
            
        backups.sort(reverse=True)
        backup_recente = backups[0]
        
        with open(backup_recente, 'r', encoding='utf-8') as f:
            codigo_backup = f.read()
        
        with open(__file__, 'w', encoding='utf-8') as f:
            f.write(codigo_backup)
            
        self.logger.critical(f"RESTAURADO BACKUP: {backup_recente}")
        return True

    async def ciclo_de_aprimoramento(self):
        self.logger.info("Iniciando ciclo de autoaprimoramento...")
        codigo = self.ler_codigo_fonte()
        
        # Verificador de falha crítica antes de continuar
        if re.search(r"Traceback|FATAL|CRITICAL", self.log_anterior):
            self.logger.warning("Falha crítica detectada na execução anterior")
            if self.restaurar_backup_recente():
                self.logger.info("Reiniciando com versão estável...")
                subprocess.Popen([sys.executable, __file__])
                exit(0)
        
        self.logger.info("Consultando cérebro especialista em código...")
        hipotese_bruta = await self.cerebro.gerar_hipotese(codigo, self.log_anterior)
        self.logger.info("Hipótese bruta recebida")
        
        # Verificar se é um comando de instalação
        try:
            resposta = json.loads(hipotese_bruta)
            if resposta.get('acao') == 'instalar':
                pacote = resposta.get('pacote')
                if pacote:
                    self.logger.info(f"Instalando pacote: {pacote}")
                    if self.instalar_dependencia(pacote):
                        self.logger.info("Reiniciando agente após instalação...")
                        with open("agente_hifen.log", "r") as log_file:
                            log_atual = log_file.read()
                        subprocess.run([sys.executable, __file__, base64.b64encode(log_atual.encode()).decode()])
                        exit(0)
                    else:
                        self.logger.error("Falha na instalação, ciclo abortado.")
                        return
        except json.JSONDecodeError:
            pass  # Não é um JSON, continua o fluxo normal
        
        hipotese_limpa = self.limpar_hipotese(hipotese_bruta)
        
        if self.validar_hipotese(hipotese_limpa):
            self.aplicar_modificacao(codigo, hipotese_limpa)
        else:
            self.logger.error("Ciclo abortado. A hipótese foi descartada por ser inválida.")

if __name__ == "__main__":
    os.makedirs("backup_logs", exist_ok=True)
    log_anterior = ""
    
    if len(sys.argv) > 1:
        try:
            log_anterior = base64.b64decode(sys.argv[1].encode()).decode()
        except:
            log_anterior = sys.argv[1]
    
    if not os.path.exists(".env"):
        api_key = input("Por favor, insira sua chave API da OpenRouter: ")
        with open(".env", "w") as f:
            f.write(f"OPENROUTER_API_KEY={api_key}")
    
    agente = AgentHifen(log_anterior=log_anterior)
    asyncio.run(agente.ciclo_de_aprimoramento())