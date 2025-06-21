import base64
import json
import subprocess
import sys
import ast
import hashlib
from pathlib import Path

from utils import setup_logger, criar_backup
from agente_autonomo.src.cerebro import CerebroExterno

AGENT_FILE = Path(__file__)
STATE_FILE = Path("agent_state.json")
LOG_FILE = Path("agente_hifen.log")

logger = setup_logger(LOG_FILE, "agente_hifen")


def _load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except Exception:
            return {}
    return {}


def _save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state))


def _update_error_state(log: str, threshold: int = 3) -> bool:
    """Update state with the hash of ``log`` and return True if threshold exceeded."""
    if not log:
        _save_state({})
        return False

    state = _load_state()
    h = hashlib.sha256(log.encode()).hexdigest()
    if state.get("error_hash") == h:
        state["count"] = state.get("count", 0) + 1
    else:
        state = {"error_hash": h, "count": 1}
    _save_state(state)
    return state["count"] >= threshold


def _validate_code(code: str) -> bool:
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        logger.error("Codigo invalido: %s", e)
        return False
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            return True
    logger.error("Codigo recebido sem funcoes ou classes")
    return False


def _rewrite_self(new_code: str) -> None:
    if not _validate_code(new_code):
        logger.error("Nova versao falhou na validacao")
        return
    backup_path = criar_backup(AGENT_FILE)
    AGENT_FILE.write_text(new_code)
    logger.info("Arquivo atualizado. Backup criado em %s", backup_path)


def _diagnosticar(log: str, source: str) -> dict:
    cerebro = CerebroExterno()
    if "ModuleNotFoundError" in log:
        prompt = (
            "Analise o log a seguir e informe em JSON o pacote faltante.\n"
            f"LOG:\n{log}\n"
            "Responda somente no formato {\"package\": \"nome\"}."
        )
        resp = cerebro.gerar_resposta(prompt)
        try:
            data = json.loads(resp)
            pkg = data.get("package")
            if pkg:
                return {"action": "install", "package": pkg}
        except Exception as e:
            logger.error("Falha ao interpretar JSON: %s", e)
        return {"action": "none"}

    if "Traceback" in log:
        prompt = (
            "Corrija o erro no codigo abaixo com base no log fornecido.\n"
            f"LOG:\n{log}\n"
            f"CODIGO ATUAL:\n{source}\n"
            "Retorne apenas o codigo atualizado."
        )
        code = cerebro.gerar_resposta(prompt)
        return {"action": "rewrite", "code": code}

    prompt = (
        "Sugira uma nova otimizacao ou funcionalidade e forneca o codigo completo\n"
        f"CODIGO ATUAL:\n{source}\n"
        "Retorne apenas o codigo atualizado."
    )
    code = cerebro.gerar_resposta(prompt)
    return {"action": "rewrite", "code": code}


def main(encoded_log: str | None = None) -> None:
    log_text = ""
    if encoded_log:
        try:
            log_text = base64.b64decode(encoded_log).decode()
        except Exception:
            logger.error("Falha ao decodificar log")
            log_text = ""

    if _update_error_state(log_text):
        logger.error("Mesmo erro repetido varias vezes. Abortando.")
        return

    source = AGENT_FILE.read_text()
    result = _diagnosticar(log_text, source)

    if result.get("action") == "install" and result.get("package"):
        pkg = result["package"]
        logger.info("Instalando dependencia %s", pkg)
        subprocess.run([sys.executable, "-m", "pip", "install", pkg])
        return

    if result.get("action") == "rewrite" and result.get("code"):
        _rewrite_self(result["code"])
        return


if __name__ == "__main__":
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    main(arg)
