import os
import sys
import time
from pathlib import Path
from getpass import getpass
import subprocess
import requests

ROOT = Path(__file__).parent
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
FRONTEND_PORT = os.environ.get("FRONTEND_PORT", "5173")
KEY_FILE = ROOT / ".openrouter_key"
DATA_AGENTES = ROOT / "agentes.json"
DATA_LOCAIS = ROOT / "locais.json"


def ensure_api_key() -> None:
    """Solicita e armazena a API Key da OpenRouter na primeira execucao."""
    if KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
    else:
        key = getpass("Digite sua OpenRouter API Key: ")
        KEY_FILE.write_text(key)
    os.environ["OPENROUTER_API_KEY"] = key


def install_dependencies() -> None:
    """Instala dependencias do backend e frontend se necessario."""
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)
    node_modules = ROOT / "dashboard" / "node_modules"
    if not node_modules.exists():
        subprocess.run(["npm", "install"], cwd=ROOT / "dashboard", check=True)


def wait_backend(port: str, timeout: int = 30) -> bool:
    url = f"http://localhost:{port}/locais"
    for _ in range(timeout):
        try:
            requests.get(url, timeout=1)
            return True
        except Exception:
            time.sleep(1)
    return False


def show_status(port: str) -> None:
    try:
        ag = requests.get(f"http://localhost:{port}/agentes", timeout=5).json()
        loc = requests.get(f"http://localhost:{port}/locais", timeout=5).json()
        print("Agentes criados:", ", ".join(a["nome"] for a in ag))
        print("Salas criadas:", ", ".join(l["nome"] for l in loc))
    except Exception as exc:
        print("Nao foi possivel obter informacoes iniciais:", exc)


def main() -> None:
    ensure_api_key()
    install_dependencies()
    print("Arquivos de dados serao armazenados em:")
    print(f"  Agentes: {DATA_AGENTES}")
    print(f"  Locais: {DATA_LOCAIS}")

    backend_cmd = [sys.executable, "-m", "uvicorn", "api:app", "--reload", "--port", BACKEND_PORT]
    backend_log = open(ROOT / "backend.log", "w")
    backend = subprocess.Popen(backend_cmd, stdout=backend_log, stderr=subprocess.STDOUT)
    if not wait_backend(BACKEND_PORT):
        print("Backend nao respondeu a tempo.")
        backend.terminate()
        backend_log.close()
        return
    print(f"Backend rodando em http://localhost:{BACKEND_PORT}")
    show_status(BACKEND_PORT)
    # Gatilho do primeiro ciclo automatico logo apos o backend iniciar
    try:
        requests.post(f"http://localhost:{BACKEND_PORT}/ciclo/next", timeout=5)
    except Exception as exc:
        print("Falha ao disparar ciclo inicial:", exc)

    frontend_cmd = ["npm", "run", "dev", "--", "--port", FRONTEND_PORT]
    frontend_log = open(ROOT / "frontend.log", "w")
    frontend = subprocess.Popen(frontend_cmd, cwd=ROOT / "dashboard", stdout=frontend_log, stderr=subprocess.STDOUT)
    print(f"Frontend acessivel em http://localhost:{FRONTEND_PORT}")

    try:
        while True:
            if backend.poll() is not None:
                print("Backend finalizado inesperadamente. Veja backend.log")
                break
            if frontend.poll() is not None:
                print("Frontend finalizado inesperadamente. Veja frontend.log")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        frontend.terminate()
        backend.terminate()
        frontend.wait()
        backend.wait()
        backend_log.close()
        frontend_log.close()


if __name__ == "__main__":
    main()
