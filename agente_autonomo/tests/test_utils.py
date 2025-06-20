from src.utils import VersaoAnterior
from pathlib import Path


def test_backup_criado(tmp_path):
    backup = VersaoAnterior('conteudo de teste', 'teste')
    backup_path = backup.salvar()
    assert backup_path.exists()
    assert backup_path.read_text() == 'conteudo de teste'
    # cleanup
    backup_path.unlink()
