import os
import json
from pathlib import Path
from typing import List, Tuple
import requests

ROOT = Path(__file__).parent
KEY_FILE = ROOT / ".openrouter_key"


def obter_api_key() -> str:
    """Retorna a chave da OpenRouter da variavel de ambiente ou arquivo."""
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key.strip()
    if KEY_FILE.exists():
        key = KEY_FILE.read_text().strip()
        os.environ["OPENROUTER_API_KEY"] = key
        return key
    raise RuntimeError("OPENROUTER_API_KEY nao definido")


def buscar_modelos_gratis() -> List[str]:
    """Lista todos os modelos gratuitos fornecidos pela OpenRouter."""
    key = obter_api_key()
    url = "https://openrouter.ai/api/v1/models"
    resp = requests.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=10)
    resp.raise_for_status()
    data = resp.json()
    return [m.get("id") for m in data.get("data", []) if ":free" in m.get("id", "")]


def escolher_modelo_llm(funcao: str, objetivo: str, modelos: List[str]) -> Tuple[str, str]:
    """Usa uma LLM real para definir o modelo mais adequado."""
    key = obter_api_key()
    prompt = (
        "Voce e um assistente responsavel por escolher qual modelo gratuito deve ser usado por um agente da empresa. "
        "Considere a funcao e a tarefa atual. Responda apenas em JSON com as chaves 'modelo' e 'raciocinio'."
    )
    user = f"Funcao: {funcao}\nObjetivo ou tarefa: {objetivo}\nModelos disponiveis: {', '.join(modelos)}"
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": user},
        ],
    }
    resp = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json=payload,
        timeout=20,
    )
    resp.raise_for_status()
    answer = resp.json()["choices"][0]["message"]["content"].strip()
    try:
        data = json.loads(answer)
        modelo = data.get("modelo") or (modelos[0] if modelos else "")
        raciocinio = data.get("raciocinio", "")
    except Exception:
        modelo = modelos[0] if modelos else ""
        raciocinio = f"Resposta invalida: {answer}"
    return modelo, raciocinio
