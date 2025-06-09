import os
import sys
from pathlib import Path
from getpass import getpass
import argparse
import requests

ROOT = Path(__file__).parent
KEY_FILE = ROOT / ".openrouter_key"
DEFAULT_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")


def ensure_api_key() -> str:
    """Garantir que a OpenRouter API Key esteja configurada."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    if KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
    else:
        key = getpass("Digite sua OpenRouter API Key: ")
        KEY_FILE.write_text(key)
    os.environ["OPENROUTER_API_KEY"] = key
    return key


def list_agents(base_url: str) -> None:
    resp = requests.get(f"{base_url}/agentes", timeout=10)
    resp.raise_for_status()
    for ag in resp.json():
        print(f"- {ag['nome']} ({ag['funcao']}) - {ag['local_atual']}")


def list_rooms(base_url: str) -> None:
    resp = requests.get(f"{base_url}/locais", timeout=10)
    resp.raise_for_status()
    for loc in resp.json():
        print(f"- {loc['nome']}: {loc['descricao']}")


def run_cycle(base_url: str) -> None:
    resp = requests.post(f"{base_url}/ciclo/next", timeout=10)
    resp.raise_for_status()
    data = resp.json()
    print("Saldo:", data["saldo"])
    print("Eventos:")
    for e in data.get("eventos", []):
        print("  ", e)


def list_models(base_url: str) -> None:
    ensure_api_key()
    resp = requests.get(f"{base_url}/modelos-livres", timeout=10)
    resp.raise_for_status()
    for m in resp.json():
        print("-", m)


def main() -> None:
    parser = argparse.ArgumentParser(description="CLI para Empresa Digital")
    parser.add_argument(
        "command",
        choices=["agentes", "locais", "ciclo", "modelos"],
        help="Acao a executar",
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help="URL base do backend (padrao: http://localhost:8000)",
    )
    args = parser.parse_args()

    if args.command == "agentes":
        list_agents(args.url)
    elif args.command == "locais":
        list_rooms(args.url)
    elif args.command == "ciclo":
        run_cycle(args.url)
    elif args.command == "modelos":
        list_models(args.url)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
