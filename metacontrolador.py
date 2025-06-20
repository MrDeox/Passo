import os
import subprocess
import json
import glob
import hashlib
import base64
import asyncio
import sys
import logging
from dotenv import load_dotenv
from openai import AsyncOpenAI

# Configuração do logger
def setup_logger(name, log_file='metacontrolador.log', level=logging.INFO):
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

    async def consultar_llm(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model="deepseek/deepseek-r1-0528:free",
            messages=[{
                "role": "user",
                "content": prompt
            }],
            extra_headers={
                "HTTP-Referer": "https://github.com/arthurprojects/Passo",
                "X-Title": "Metacontrolador Evolutivo"
            }
        )
        return response.choices[0].message.content

class Metacontrolador:
    def __init__(self):
        self.logger = setup_logger('Metacontrolador')
        self.cerebro = CerebroExterno()
        self.backup_dir = "."
        self.log_anterior = ""
        self.logger.info("Metacontrolador inicializado")

    async def executar_ciclo_evolutivo(self) -> str:
        self.logger.info("Executando ciclo evolutivo...")
        args = [sys.executable, 'agente_hifen.py']
        if self.log_anterior:
            log_b64 = base64.b64encode(self.log_anterior.encode()).decode()
            args.append(log_b64)
            
        try:
            result = subprocess.run(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                timeout=300  # 5 minutos de timeout
            )
            log = f"STDOUT:\n{result.stdout}\n\nSTDERR:\n{result.stderr}"
            return log
        except subprocess.TimeoutExpired:
            self.logger.critical("Timeout excedido (5 minutos) ao executar ciclo evolutivo.")
            return "Erro: Timeout excedido (5 minutos) ao executar ciclo evolutivo."
        except Exception as e:
            self.logger.error(f"Erro ao executar ciclo evolutivo: {str(e)}")
            return f"Erro ao executar ciclo evolutivo: {str(e)}"

    def ler_historico_de_backups(self, backup_files: list) -> list:
        self.logger.debug("Lendo histórico de backups...")
        backups = sorted(backup_files, key=os.path.getmtime, reverse=True)
        
        historico = []
        for backup in backups:
            with open(backup, 'r', encoding='utf-8') as f:
                historico.append({
                    'arquivo': backup,
                    'conteudo': f.read(),
                    'hash': hashlib.md5(f.read().encode()).hexdigest()
                })
        return historico

    async def gerar_sumario_evolutivo(self, historico_codigos: list, logs_da_sessao: list) -> str:
        self.logger.info("Gerando sumário evolutivo...")
        prompt = """Analise esta sequência de códigos e os logs de execução correspondentes. 
Crie um sumário conciso das principais mudanças e melhorias implementadas ao longo dessas versões, 
levando em conta os erros que ocorreram e como eles foram resolvidos.

"""
        for i, versao in enumerate(historico_codigos):
            prompt += f"\n=== VERSÃO {i+1} ({versao['arquivo']}) ===\n"
            prompt += f"[CÓDIGO]\n{versao['conteudo']}\n"
            
            if i < len(logs_da_sessao):
                log = logs_da_sessao[i]
                prompt += f"[LOG DA EXECUÇÃO]\n{log[:2000]}{'...' if len(log)>2000 else ''}\n\n"

        return await self.cerebro.consultar_llm(prompt)

    async def reagir_ao_sumario(self, sumario: str) -> dict:
        self.logger.info("Gerando avaliação do sumário...")
        prompt = f"""Dado este sumário da minha evolução recente, avalie se a direção geral foi positiva ou negativa para meu objetivo de me tornar um agente econômico autônomo. 
Dê uma nota de -10 (muito negativo) a +10 (muito positivo) e uma justificativa curta.

SUMÁRIO:
{sumario}

Por favor, responda no formato JSON com as chaves 'nota' (número) e 'justificativa' (string)."""

        resposta = await self.cerebro.consultar_llm(prompt)
        try:
            return json.loads(resposta)
        except json.JSONDecodeError:
            return {'nota': 0, 'justificativa': 'Não foi possível avaliar'}

    async def orquestrar_analise(self, num_ciclos: int = 5):
        self.logger.info(f"Iniciando análise de evolução com {num_ciclos} ciclos...")
        
        backups_iniciais = set(glob.glob(os.path.join(self.backup_dir, 'backup_*.py')))
        
        logs_da_sessao = []
        for i in range(num_ciclos):
            self.logger.info(f"Executando ciclo evolutivo {i+1}/{num_ciclos}...")
            log = await self.executar_ciclo_evolutivo()
            logs_da_sessao.append(log)
            self.log_anterior = log

        self.logger.info("Fase de evolução concluída. Iniciando fase de reflexão...")
        backups_finais = set(glob.glob(os.path.join(self.backup_dir, 'backup_*.py')))
        backups_desta_sessao = list(backups_finais - backups_iniciais)
        
        if not backups_desta_sessao:
            self.logger.error("Reflexão abortada: Nenhum ciclo de evolução foi concluído com sucesso nesta sessão.")
            return
            
        historico = self.ler_historico_de_backups(backups_desta_sessao)
        sumario = await self.gerar_sumario_evolutivo(historico, logs_da_sessao)
        
        self.logger.info("=== SUMÁRIO EVOLUTIVO ===")
        self.logger.info(sumario)
        
        avaliacao = await self.reagir_ao_sumario(sumario)
        self.logger.info("=== AVALIAÇÃO ===")
        self.logger.info(f"Nota: {avaliacao['nota']}/10")
        self.logger.info(f"Justificativa: {avaliacao['justificativa']}")

if __name__ == "__main__":
    import asyncio
    controlador = Metacontrolador()
    asyncio.run(controlador.orquestrar_analise())
