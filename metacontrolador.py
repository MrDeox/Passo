"""Supervisor Imortal for the autonomous agent.

This module repeatedly executes ``agente.py`` while capturing its output and
feeding the log of the previous execution into the next run. All actions are
logged using the utility logger configuration.
"""

from __future__ import annotations

import base64
import subprocess
import sys
import time
from pathlib import Path

from utils import setup_logger

AGENT_PATH = Path("agente_autonomo/src/agente.py")
LOG_FILE = Path("metacontrolador.log")


def _run_agent(memory: str, timeout: int = 60) -> tuple[str, str]:
    """Execute ``agente.py`` with the provided memory string.

    Parameters
    ----------
    memory : str
        Encoded memory from the previous cycle.
    timeout : int, optional
        Maximum execution time in seconds before the process is killed.

    Returns
    -------
    tuple[str, str]
        A tuple containing ``stdout`` and ``stderr`` captured from the
        ``agente.py`` execution.
    """

    cmd = [sys.executable, str(AGENT_PATH)]
    if memory:
        encoded = base64.b64encode(memory.encode()).decode()
        cmd.append(encoded)

    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    try:
        stdout, stderr = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        proc.kill()
        stdout, stderr = proc.communicate()
        stderr = (stderr or "") + "\n[Supervisor] Processo encerrado por timeout."

    return stdout, stderr


def supervisao(ciclos: int | None = None, intervalo: int = 1, timeout: int = 60) -> None:
    """Execute ``agente.py`` em ciclos contínuos.

    Parameters
    ----------
    ciclos : int | None, optional
        Número de ciclos a executar. ``None`` indica execução infinita.
    intervalo : int, optional
        Intervalo em segundos entre cada execução do agente.
    timeout : int, optional
        Tempo máximo para cada execução do agente.
    """

    logger = setup_logger(LOG_FILE, logger_name="metacontrolador")
    memoria: str = ""
    count = 0

    while True:
        if ciclos is not None and count >= ciclos:
            logger.info("Execução finalizada após %d ciclo(s)", count)
            break

        count += 1
        logger.info("Iniciando ciclo %d", count)
        stdout, stderr = _run_agent(memoria, timeout=timeout)
        if stdout:
            logger.info("STDOUT:\n%s", stdout)
        if stderr:
            logger.error("STDERR:\n%s", stderr)
        memoria = stdout + stderr
        time.sleep(intervalo)


if __name__ == "__main__":
    supervisao()
