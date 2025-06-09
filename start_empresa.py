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

    backend_cmd = [sys.executable, "-m", "uvicorn", "api:app", "--reload", "--port", BACKEND_PORT]
    backend = subprocess.Popen(backend_cmd)
    if not wait_backend(BACKEND_PORT):
        print("Backend nao respondeu a tempo.")
        backend.terminate()
        return
    print(f"Backend rodando em http://localhost:{BACKEND_PORT}")
    show_status(BACKEND_PORT)

    frontend_cmd = ["npm", "run", "dev", "--", "--port", FRONTEND_PORT]
    frontend = subprocess.Popen(frontend_cmd, cwd=ROOT / "dashboard")
    print(f"Frontend acessivel em http://localhost:{FRONTEND_PORT}")

    try:
        while True:
            time.sleep(1)
            if backend.poll() is not None or frontend.poll() is not None:
                break
    except KeyboardInterrupt:
        pass
    finally:
        frontend.terminate()
        backend.terminate()
        frontend.wait()
        backend.wait()


if __name__ == "__main__":
    main()
