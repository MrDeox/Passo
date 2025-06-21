import os
import re
import logging
from pathlib import Path

import pytest

from utils import setup_logger, criar_backup


def test_setup_logger_creates_file_and_logs(tmp_path, capsys):
    log_path = tmp_path / "logfile.log"
    logger = setup_logger(log_path, logger_name="test_logger")
    logger.info("hello")

    captured = capsys.readouterr()
    assert "hello" in captured.err or "hello" in captured.out

    assert log_path.exists()
    assert "hello" in log_path.read_text()


def test_setup_logger_idempotent(tmp_path):
    log_path = tmp_path / "logfile.log"
    logger1 = setup_logger(log_path, logger_name="test_logger_idem")
    handlers_first = len(logger1.handlers)

    logger2 = setup_logger(log_path, logger_name="test_logger_idem")
    handlers_second = len(logger2.handlers)

    assert logger1 is logger2
    assert handlers_first == handlers_second == 2


def test_criar_backup(tmp_path):
    file_path = tmp_path / "original.txt"
    file_path.write_text("conteudo")

    backup_path = criar_backup(file_path)

    assert backup_path.exists()
    assert file_path.read_text() == backup_path.read_text()
    assert file_path.read_text() == "conteudo"

    pattern = re.compile(r"original.txt\.backup_\d{8}_\d{6}$")
    assert pattern.search(str(backup_path))


def test_criar_backup_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        criar_backup(tmp_path / "nao_existe.txt")


if __name__ == "__main__":
    import pytest

    raise SystemExit(pytest.main([__file__]))
