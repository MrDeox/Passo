import logging
from pathlib import Path

LOG_DIR = Path('logs')
LOG_DIR.mkdir(exist_ok=True)

BACKUP_DIR = Path('backups')
BACKUP_DIR.mkdir(exist_ok=True)

class VersaoAnterior:
    def __init__(self, content: str, name_prefix: str = 'backup'):
        self.content = content
        self.name_prefix = name_prefix

    def salvar(self) -> Path:
        index = len(list(BACKUP_DIR.glob(f'{self.name_prefix}_*.txt')))
        path = BACKUP_DIR / f"{self.name_prefix}_{index}.txt"
        path.write_text(self.content)
        return path

def setup_logger(name: str, logfile: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(LOG_DIR / logfile)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    fh.setFormatter(formatter)
    logger.addHandler(fh)
    return logger
