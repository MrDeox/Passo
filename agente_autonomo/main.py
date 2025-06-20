import subprocess
import sys
from pathlib import Path
from src.utils import setup_logger, VersaoAnterior

LOG_FILE = Path('logs/main.log')
logger = setup_logger('main', 'main.log')

BACKUP_DIR = Path('backups')


def executar_agente(log_anterior: str) -> str:
    processo = subprocess.Popen([sys.executable, 'src/agente.py', log_anterior], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    stdout, stderr = processo.communicate()
    if stdout:
        logger.info(stdout)
    if stderr:
        logger.error(stderr)
    return stderr


def ciclo():
    logger.info('Iniciando ciclo do Metacontrolador')
    log_anterior = ''
    backup_files = sorted(BACKUP_DIR.glob('log_*.txt'))
    if backup_files:
        ultimo = backup_files[-1]
        log_anterior = ultimo.read_text()
    erro = executar_agente(log_anterior)
    if erro:
        VersaoAnterior(erro, 'erro').salvar()
        logger.error('Erro registrado e salvo')
    else:
        logger.info('Ciclo executado sem erros')


if __name__ == '__main__':
    ciclo()
