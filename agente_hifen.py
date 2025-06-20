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
# from datetime import datetime # Movido para utils.py
from dotenv import load_dotenv
from openai import AsyncOpenAI
from utils import VersaoAnterior # Importa a nova classe

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
        self.version_manager = VersaoAnterior(agent_file_path=__file__) # Instancia o gestor de versão
        self.logger.info(f"AgentHifen inicializado (restart #{self.restart_count})")
    
    # def criar_backup(self, codigo: str) -> None: # Movido para VersaoAnterior
    #     """Cria backup do código atual com timestamp"""
    #     timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    #     backup_path = f"backup_logs/backup_{timestamp}.py"
    #     with open(backup_path, 'w', encoding='utf-8') as f:
    #         f.write(codigo)
    #     self.logger.info(f"Backup criado: {backup_path}")

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
        MIN_LENGTH = 500  # Valor mínimo razoável para um programa Python
        
        try:
            # Primeiro, verificar o tamanho mínimo
            if len(codigo_hipotetico) < MIN_LENGTH:
                self.logger.error(f"Código muito curto ({len(codigo_hipotetico)} caracteres). Possível resposta incompleta.")
                return False
                
            # Verificar se o código pode ser analisado pelo AST
            ast.parse(codigo_hipotetico)
            
            # Verificar estruturas essenciais
            estruturas_essenciais = [
                "import",  # Deve ter pelo menos um import
                "class AgentHifen",  # Classe principal
                'if __name__ == "__main__":'  # Bloco principal
            ]
            
            for estrutura in estruturas_essenciais:
                if estrutura not in codigo_hipotetico:
                    self.logger.error(f"Estrutura essencial ausente: '{estrutura}'")
                    return False
                    
            self.logger.info("Validação bem-sucedida")
            return True
            
        except Exception as e:
            self.logger.error(f"Falha na validação AST: {e}")
            return False

    def aplicar_modificacao(self, codigo_atual: str, codigo_novo: str) -> None:
        self.logger.info("Aplicando modificação...")
        self.version_manager.criar_backup(codigo_atual)  # Backup antes de modificar
        
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

    # def restaurar_backup_recente(self) -> bool: # Movido para VersaoAnterior
    #     """Restaura o backup mais recente em caso de falha crítica"""
    #     backups = glob.glob("backup_logs/backup_*.py")
    #     if not backups:
    #         return False
            
    #     backups.sort(reverse=True)
    #     backup_recente = backups[0]
        
    #     with open(backup_recente, 'r', encoding='utf-8') as f:
    #         codigo_backup = f.read()
        
    #     with open(__file__, 'w', encoding='utf-8') as f:
    #         f.write(codigo_backup)
            
    #     self.logger.critical(f"RESTAURADO BACKUP: {backup_recente}")
    #     return True

    async def ciclo_de_aprimoramento(self):
        self.logger.info("Iniciando ciclo de autoaprimoramento...")
        codigo = self.ler_codigo_fonte()
        
        # Verificador de falha crítica antes de continuar
        if re.search(r"Traceback|FATAL|CRITICAL", self.log_anterior, re.IGNORECASE):
            self.logger.warning("Falha crítica detectada na execução anterior")
            # Usa o version_manager para restaurar o backup
            if self.version_manager.restaurar_backup_recente():
                self.logger.info("Reiniciando com versão estável...")
                # Passa o log anterior vazio para evitar loop de restauração se o backup também falhar
                subprocess.Popen([sys.executable, __file__, "", str(self.restart_count + 1)])
                exit(0)
            else:
                self.logger.error("Falha ao restaurar backup. O agente pode estar em um estado irrecuperável.")
                # Considerar uma ação mais drástica aqui se necessário
                return # Aborta o ciclo
        
        # Limite máximo de reinicializações
        if self.restart_count > 5:
            self.logger.critical("Limite máximo de reinicializações alcançado! Abortando.")
            return
            
        self.logger.info("Consultando cérebro especialista em código...")
        hipotese_bruta = await self.cerebro.gerar_hipotese(codigo, self.log_anterior)
        self.logger.info("Hipótese bruta recebida")

        # Nova lógica de detecção e tratamento de ModuleNotFoundError
        if "ModuleNotFoundError" in self.log_anterior:
            self.logger.info("Detectado 'ModuleNotFoundError' no log anterior.")
            match = re.search(r"No module named '([^']*)'", self.log_anterior)
            if match:
                nome_modulo = match.group(1)
                self.logger.info(f"Módulo ausente identificado: {nome_modulo}")
                if await self.instalar_dependencia(nome_modulo):
                    self.logger.info(f"Módulo {nome_modulo} instalado. Reiniciando para aplicar alterações.")
                    # Reinicia o agente, idealmente o log anterior para a próxima execução não conterá o ModuleNotFoundError
                    # ou será o log da própria instalação.
                    # Passa um log_anterior vazio ou um log específico da instalação.
                    # Incrementa o restart_count para o reinício.
                    current_log = "" # Poderia ser o log da instalação se fosse capturado de forma útil
                    try:
                        with open("agente_hifen.log", "r") as log_file: # Pega o log atual para passar adiante
                           current_log = log_file.read()
                    except Exception as e:
                        self.logger.error(f"Nao foi possivel ler o log do agente: {e}")

                    os.environ["AGENT_RESTART_COUNT"] = str(self.restart_count + 1)
                    subprocess.Popen([
                        sys.executable,
                        __file__,
                        base64.b64encode(current_log.encode()).decode(), # Passa o log atual como log_anterior
                        str(self.restart_count + 1)
                    ])
                    exit(0)
                else:
                    self.logger.error(f"Falha ao instalar o módulo {nome_modulo}. O agente pode não conseguir continuar.")
                    # Decide se aborta ou tenta outra estratégia (ex: pedir ajuda ao LLM para corrigir o nome do pacote)
                    return # Aborta o ciclo atual
            else:
                self.logger.warning("ModuleNotFoundError detectado, mas não foi possível extrair o nome do módulo.")
        
        # Verificar se a hipótese bruta é um comando de instalação JSON (do LLM)
        # Esta lógica é mantida caso o LLM sugira uma instalação diretamente.
        try:
            resposta_json = json.loads(self.limpar_hipotese(hipotese_bruta)) # Limpa antes de tentar o parse
            if isinstance(resposta_json, dict) and resposta_json.get('acao') == 'instalar':
                pacote = resposta_json.get('pacote')
                if pacote:
                    self.logger.info(f"LLM solicitou instalação do pacote: {pacote}")
                    if await self.instalar_dependencia(pacote):
                        self.logger.info(f"Pacote {pacote} instalado por solicitação do LLM. Reiniciando...")
                        current_log = ""
                        try:
                            with open("agente_hifen.log", "r") as log_file:
                               current_log = log_file.read()
                        except Exception as e:
                            self.logger.error(f"Nao foi possivel ler o log do agente: {e}")

                        os.environ["AGENT_RESTART_COUNT"] = str(self.restart_count + 1)
                        subprocess.Popen([
                            sys.executable,
                            __file__,
                            base64.b64encode(current_log.encode()).decode(),
                            str(self.restart_count + 1)
                        ])
                        exit(0)
                    else:
                        self.logger.error(f"Falha ao instalar o pacote {pacote} solicitado pelo LLM. Abortando ciclo.")
                        return
        except json.JSONDecodeError:
            # Não é um JSON de instalação, provavelmente é código
            pass
        
        hipotese_limpa = self.limpar_hipotese(hipotese_bruta)
        
        # A validação e aplicação ocorrem apenas se não houver uma ação de instalação bem-sucedida que reinicie o agente
        # ou se a hipótese não for um JSON de instalação.
        # Se a hipotese_limpa for um JSON (ex: comando de instalação que falhou em ser tratado acima ou outro comando JSON),
        # não deve ser tratado como código para aplicar_modificacao.
        is_json_command = False
        try:
            json_object = json.loads(hipotese_limpa)
            if isinstance(json_object, dict) and "acao" in json_object:
                is_json_command = True
                self.logger.info(f"Hipótese limpa é um comando JSON: {hipotese_limpa}, não será aplicada como código.")
        except json.JSONDecodeError:
            pass # Não é JSON, provavelmente código

        if not is_json_command:
            if self.validar_hipotese(hipotese_limpa):
                self.aplicar_modificacao(codigo, hipotese_limpa)
            else:
                self.logger.error("Ciclo abortado. A hipótese de modificação de código foi descartada por ser inválida. Nenhuma modificação aplicada.")
                return # Aborta o ciclo se a modificação do código for inválida
        elif not hipotese_limpa: # Se a hipótese bruta era vazia e a limpa também é
             self.logger.error("Hipótese bruta ou limpa está vazia. Nenhuma ação tomada.")
             return


if __name__ == "__main__":
    # O diretório de logs de backup agora é criado pela instância de VersaoAnterior,
    # mas podemos garantir que exista aqui também, caso seja usado antes da instanciação.
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
