import os
import sys
import time
from pathlib import Path
import argparse
import subprocess
import requests
from getpass import getpass # Added from start_empresa.py

ROOT = Path(__file__).parent
BACKEND_PORT = os.environ.get("BACKEND_PORT", "8000")
KEY_FILE = ROOT / ".openrouter_key"
DATA_AGENTES = ROOT / "agentes.json"
DATA_LOCAIS = ROOT / "locais.json"

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Inicia o backend da empresa") # Kept from start_backend.py
    parser.add_argument("--apikey", help="Chave da OpenRouter")
    parser.add_argument(
        "--infinite",
        action="store_true",
        help="Ativa o modo Vida Infinita durante a simulacao",
    )
    return parser.parse_args()

def ensure_api_key() -> None:
    """Solicita e armazena a API Key da OpenRouter na primeira execucao.""" # Docstring from start_empresa.py
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        # Ensure the environment variable is stripped, even if already set
        os.environ["OPENROUTER_API_KEY"] = key.strip()
        return
    if KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
        os.environ["OPENROUTER_API_KEY"] = key # Set it for current session
        return # Added return
    else: # Modified else from start_empresa.py
        key = getpass("Digite sua OpenRouter API Key: ")
        KEY_FILE.write_text(key)
    os.environ["OPENROUTER_API_KEY"] = key.strip() # Ensure it's stripped and set

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
        print("Agentes:", ", ".join(a["nome"] for a in ag)) # Adjusted print from start_backend.py
        print("Salas:", ", ".join(l["nome"] for l in loc)) # Adjusted print from start_backend.py
    except Exception as exc:
        print(f"Nao foi possivel obter informacoes iniciais: {exc}")

def main() -> None:
    args = parse_args()
    if args.apikey:
        os.environ["OPENROUTER_API_KEY"] = args.apikey.strip()
    if args.infinite:
        os.environ["MODO_VIDA_INFINITA"] = "1"
    ensure_api_key()
    install_dependencies()
    print("Arquivos de dados serao armazenados em:")
    print(f"  Agentes: {DATA_AGENTES}")
    print(f"  Locais: {DATA_LOCAIS}")

    backend_cmd = [sys.executable, "-m", "uvicorn", "api:app", "--host", "0.0.0.0", "--port", BACKEND_PORT]
    backend_log = open(ROOT / "backend.log", "w")
    print("Iniciando backend... Logs em backend.log")
    backend = subprocess.Popen(backend_cmd, stdout=backend_log, stderr=subprocess.STDOUT)

    try:
        if not wait_backend(BACKEND_PORT):
            print("Backend nao respondeu a tempo.")
            backend.terminate()
            backend.wait()
            if backend_log: backend_log.close()
            return
        print(f"Backend rodando em http://localhost:{BACKEND_PORT}")
        show_status(BACKEND_PORT)

        try:
            print("Disparando ciclo inicial...")
            requests.post(f"http://localhost:{BACKEND_PORT}/ciclo/next", timeout=10)
            print("Ciclo inicial disparado.")
        except Exception as exc:
            print(f"Falha ao disparar ciclo inicial: {exc}")

        print("Pressione Ctrl+C para encerrar.")
        while True:
            if backend.poll() is not None:
                print("Backend finalizado inesperadamente. Veja backend.log")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando backend...")
    finally:
        print("Terminando processo backend...")
        backend.terminate()
        backend.wait()
        if backend_log:
            backend_log.close()
        print("Backend encerrado.")

if __name__ == "__main__":
    main()
