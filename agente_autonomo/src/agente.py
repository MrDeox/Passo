import subprocess
import sys
import traceback
from pathlib import Path
import importlib

from .utils import setup_logger, VersaoAnterior
from .cerebro import CerebroExterno

class Agente:
    def __init__(self, log_anterior: str = ''):
        self.log_anterior = log_anterior
        self.logger = setup_logger('agente', 'agente.log')
        self.cerebro = CerebroExterno()

    def instalar_dependencia(self, package: str):
        subprocess.run([sys.executable, '-m', 'pip', 'install', package], check=False)

    def executar(self):
        self.logger.info('Iniciando ciclo de aprimoramento')
        if self.log_anterior:
            VersaoAnterior(self.log_anterior, 'log').salvar()

        try:
            prompt = f"Baseado no log: {self.log_anterior}\nProponha uma acao."
            resposta = self.cerebro.gerar_resposta(prompt)
            self.logger.info(f'Hipótese gerada: {resposta}')
            # Exemplo simples: extrair dependencias mencionadas
            if 'pip install' in resposta:
                pkg = resposta.split('pip install')[-1].strip().split()[0]
                self.instalar_dependencia(pkg)
        except ModuleNotFoundError as e:
            pkg = str(e).split("No module named")[-1].strip().strip("'")
            self.instalar_dependencia(pkg)
        except Exception:
            self.logger.error(traceback.format_exc())
            return traceback.format_exc()
        return ''

if __name__ == '__main__':
    log = sys.argv[1] if len(sys.argv) > 1 else ''
    agente = Agente(log)
    err = agente.executar()
    if err:
        print(err)
