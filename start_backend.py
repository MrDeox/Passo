import os
import sys
import time
from pathlib import Path
import subprocess
import requests

ROOT = Path(__file__).parent
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
KEY_FILE = ROOT / ".openrouter_key"
DATA_AGENTES = ROOT / "agentes.json"
DATA_LOCAIS = ROOT / "locais.json"


def ensure_api_key() -> None:
    """Define OPENROUTER_API_KEY a partir de variavel ou arquivo."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        os.environ["OPENROUTER_API_KEY"] = key.strip()
        return
    if KEY_FILE.exists():
        os.environ["OPENROUTER_API_KEY"] = KEY_FILE.read_text().strip()
        return
    raise RuntimeError(
        "Defina OPENROUTER_API_KEY ou crie o arquivo .openrouter_key com a chave"
    )


def install_dependencies() -> None:
    """Instala dependencias do backend se necessario."""
    subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], check=True)


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
        print("Agentes:", ", ".join(a["nome"] for a in ag))
        print("Salas:", ", ".join(l["nome"] for l in loc))
    except Exception as exc:
        print("Nao foi possivel obter informacoes iniciais:", exc)


def main() -> None:
    ensure_api_key()
    install_dependencies()
    print("Arquivos de dados serao armazenados em:")
    print(f"  Agentes: {DATA_AGENTES}")
    print(f"  Locais: {DATA_LOCAIS}")

    backend_cmd = [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", BACKEND_PORT]
    print("Iniciando backend...")
    backend = subprocess.Popen(backend_cmd)

    try:
        if not wait_backend(BACKEND_PORT):
            print("Backend nao respondeu a tempo.")
            backend.terminate()
            backend.wait()
            return
        print(f"Backend rodando em http://localhost:{BACKEND_PORT}")
        show_status(BACKEND_PORT)
        print("Pressione Ctrl+C para encerrar.")
        backend.wait()
    except KeyboardInterrupt:
        pass
    finally:
        backend.terminate()
        backend.wait()


if __name__ == "__main__":
    main()
