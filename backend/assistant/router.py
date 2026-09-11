"""
Route FastAPI de l'assistant Kalima.

Conçu sans état côté serveur : le frontend renvoie l'historique de la
conversation à chaque appel. Simple et suffisant pour une v1 ; on
pourra ajouter une vraie gestion de session plus tard si besoin.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .action_parser import extract_action
from .ollama_client import chat_with_kalima
from .system_prompt import KALIMA_SYSTEM_PROMPT

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ChatMessage(BaseModel):
    role: str  # "user" ou "assistant"
    content: str


class ChatRequest(BaseModel):
    history: list[ChatMessage]  # historique de la conversation, sans le system prompt


class ChatResponse(BaseModel):
    reply: str
    action: dict | None = None


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not request.history:
        raise HTTPException(status_code=400, detail="Historique vide")

    messages = [{"role": "system", "content": KALIMA_SYSTEM_PROMPT}]
    messages += [{"role": m.role, "content": m.content} for m in request.history]

    try:
        raw_reply = await chat_with_kalima(messages)
    except Exception as exc:  # Ollama down, timeout, modèle absent, etc.
        raise HTTPException(
            status_code=503,
            detail=f"Assistant indisponible pour le moment ({exc})",
        )

    visible_text, action = extract_action(raw_reply)
    return ChatResponse(reply=visible_text, action=action)
