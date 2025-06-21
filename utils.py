"""Utility functions for the autonomous agent project."""

from __future__ import annotations

import logging
import shutil
from datetime import datetime
from pathlib import Path


def setup_logger(log_file_path: str | Path, logger_name: str = "agent_logger") -> logging.Logger:
    """Configure and return a logger.

    The logger sends messages to both the console and the file provided. If the
    logger already has handlers configured for the given file or stream, they
    will not be added again.

    Parameters
    ----------
    log_file_path: str or Path
        Path of the log file to write logs to.
    logger_name: str, optional
        Name of the logger to configure. Defaults to ``"agent_logger"``.

    Returns
    -------
    logging.Logger
        The configured logger instance.
    """

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    log_path = Path(log_file_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    # Prevent duplicate handlers when the function is called multiple times.
    if not any(isinstance(h, logging.FileHandler) and h.baseFilename == str(log_path) for h in logger.handlers):
        file_handler = logging.FileHandler(log_path)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, logging.FileHandler) for h in logger.handlers):
        stream_handler = logging.StreamHandler()
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    return logger


def criar_backup(file_path: str | Path) -> Path:
    """Create a timestamped backup of ``file_path``.

    The backup is stored in the same directory as the original file with a name
    formatted as ``<name>.<ext>.backup_YYYYMMDD_HHMMSS``.

    Parameters
    ----------
    file_path: str or Path
        Path to the file that should be backed up.

    Returns
    -------
    Path
        Path to the created backup file.

    Raises
    ------
    FileNotFoundError
        If ``file_path`` does not exist.
    """

    original = Path(file_path)
    if not original.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {original}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = original.with_name(f"{original.name}.backup_{timestamp}")

    shutil.copy2(original, backup_path)
    return backup_path

