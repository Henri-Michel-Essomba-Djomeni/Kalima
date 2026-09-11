"""
Client minimal pour parler à Ollama en local.

On réutilise le même modèle (Qwen) que celui déjà utilisé ailleurs
dans Kalima, donc aucun coût supplémentaire et aucune dépendance à
une API tierce payante.
"""

import os
import httpx

# Ajuste ce nom si le modèle Qwen que tu utilises déjà a un tag différent
# (ex: "qwen2.5:7b", "qwen2.5:14b-instruct"...).
OLLAMA_MODEL = os.environ.get("KALIMA_ASSISTANT_MODEL", "qwen2.5")
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434/api/chat")

# Timeout généreux : un modèle local sur CPU peut être lent au premier appel
_TIMEOUT = httpx.Timeout(120.0)


async def chat_with_kalima(messages: list[dict]) -> str:
    """
    messages : liste de {"role": "system"|"user"|"assistant", "content": str}
    Retourne le texte brut de la réponse (bloc §ACTION§ potentiellement inclus,
    non retiré ici — c'est le rôle de action_parser).
    """
    payload = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
    }

    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        response = await client.post(OLLAMA_URL, json=payload)
        response.raise_for_status()
        data = response.json()

    # Format de réponse standard d'Ollama pour /api/chat
    return data["message"]["content"]
