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
        self.logger.debug("Iniciando chamada ao LLM com timeout...")
        
        try:
            # Tentativa principal com timeout reduzido
            try:
                response = await asyncio.wait_for(
                    self.client.chat.completions.create(
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
                        }
                    ),
                    timeout=120  # Timeout reduzido para 2 minutos
                )
            except asyncio.TimeoutError:
                self.logger.warning("Tempo limite alcançado. Tentando modelo alternativo...")
                # Fallback para modelo mais rápido
                response = await self.client.chat.completions.create(
                    model="mistralai/mistral-7b-instruct:free",
                    messages=[{
                        "role": "user",
                        "content": f"RESUMO DO PROBLEMA: AgentHifen atingiu timeout anteriormente. RESPOSTA EXIGIDA: {log_execucao}. Sua resposta DEVE ser EXTREMAMENTE CONCISA: forneça apenas o código-fonte completo corrigido ou instruções JSON diretas. Sem explicações."
                    }],
                    extra_headers={
                        "HTTP-Referer": "https://github.com/arthurprojects/Passo",
                        "X-Title": "AgentHifen Debugger"
                    },
                    max_tokens=2000
                )
            
            resposta_completa = response.choices[0].message.content
            self.logger.info("Resposta do LLM recebida com sucesso")
            return resposta_completa
        except Exception as e:
            self.logger.error(f"Erro crítico na chamada ao LLM: {str(e)}")
            return ""

class AgentHifen:
    def __init__(self, log_anterior: str = ""):
        self.logger = setup_logger('AgentHifen')
        self.cerebro = CerebroExterno()
        self.log_anterior = log_anterior
        self.restart_count = int(os.getenv("AGENT_RESTART_COUNT", "0"))
        self.logger.info(f"AgentHifen inicializado (restart #{self.restart_count})")
    
    def criar_backup(self, codigo: str) -> None:
        """Cria backup do código atual com timestamp"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = f"backup_logs/backup_{timestamp}.py"
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(codigo)
        self.logger.info(f"Backup criado: {backup_path}")

    async def instalar_dependencia(self, nome_pacote: str) -> bool:
        self.logger.debug(f"Instalando dependência: {nome_pacote}")
        try:
            # Processo assíncrono para instalação
            process = await asyncio.create_subprocess_exec(
                sys.executable, '-m', 'pip', 'install', nome_pacote,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                # Timeout para instalação (45 segundos)
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=45)
            except asyncio.TimeoutError:
                process.kill()
                self.logger.error(f"Timeout ao instalar {nome_pacote}")
                return False
                
            if process.returncode == 0:
                self.logger.info(f"Pacote {nome_pacote} instalado com sucesso!")
                return True
            else:
                self.logger.error(f"Erro ao instalar {nome_pacote}: {stderr.decode().strip()}")
                return False
        except Exception as e:
            self.logger.error(f"Falha na instalação: {str(e)}")
            return False

    def ler_codigo_fonte(self) -> str:
        self.logger.debug("Lendo código fonte...")
        with open(__file__, 'r', encoding='utf-8') as f:
            return f.read()
    
    def limpar_hipotese(self, hipotese_bruta: str) -> str:
        self.logger.debug("Limpando hipótese...")
        # Identifica qualquer formato de bloco de código
        code_blocks = re.findall(r'```(?:python)?\s*(.*?)\s*```', hipotese_bruta, re.DOTALL)
        if code_blocks:
            return code_blocks[-1].strip()
        
        # Fallback para JSON
        json_match = re.search(r'\{.*?"acao":\s*".*?".*?\}', hipotese_bruta, re.DOTALL)
        if json_match:
            return json_match.group(0).strip()
            
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
        
        # Auto-limite de reinicializações
        restart_count = self.restart_count + 1
        self.logger.info(f"Reiniciando agente #{restart_count}...")
        
        # Registra log de execução atual no histórico
        with open("agente_hifen.log", "r") as log_file:
            log_atual = log_file.read()
        log_b64 = base64.b64encode(log_atual.encode()).decode()
        
        # Execução assíncrona com nova contagem
        os.environ["AGENT_RESTART_COUNT"] = str(restart_count)
        subprocess.Popen([
            sys.executable, 
            __file__, 
            log_b64,
            str(restart_count)
        ])
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
        if re.search(r"Traceback|FATAL|CRITICAL", self.log_anterior, re.IGNORECASE):
            self.logger.warning("Falha crítica detectada na execução anterior")
            if self.restaurar_backup_recente():
                self.logger.info("Reiniciando com versão estável...")
                subprocess.Popen([sys.executable, __file__, ""])
                exit(0)
        
        # Limite máximo de reinicializações
        if self.restart_count > 5:
            self.logger.critical("Limite máximo de reinicializações alcançado! Abortando.")
            return
            
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
                    if await self.instalar_dependencia(pacote):
                        self.logger.info("Reiniciando agente após instalação...")
                        with open("agente_hifen.log", "r") as log_file:
                            log_atual = log_file.read()
                        os.environ["AGENT_RESTART_COUNT"] = str(self.restart_count)
                        subprocess.run([sys.executable, __file__, base64.b64encode(log_atual.encode()).decode()])
                        exit(0)
                    else:
                        self.logger.error("Falha na instalação. Abortando ciclo.")
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
    restart_count = 0
    
    # Processar argumentos de reinicialização
    if len(sys.argv) > 1:
        try:
            log_anterior = base64.b64decode(sys.argv[1].encode()).decode()
        except:
            log_anterior = sys.argv[1]
    
    if len(sys.argv) > 2:
        restart_count = int(sys.argv[2])
    
    os.environ["AGENT_RESTART_COUNT"] = str(restart_count)
    
    if not os.path.exists(".env"):
        api_key = input("Por favor, insira sua chave API da OpenRouter: ")
        with open(".env", "w") as f:
            f.write(f"OPENROUTER_API_KEY={api_key}")
    
    agente = AgentHifen(log_anterior=log_anterior)
    asyncio.run(agente.ciclo_de_aprimoramento())