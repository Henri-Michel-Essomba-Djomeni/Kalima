"""
Résumé d'une transcription via LLM local (Ollama / Qwen 3).

Nécessite Ollama -- pas de repli vers M2M-100 pour cette fonctionnalité,
car M2M-100 ne sait que traduire, pas résumer du texte libre. Si Ollama
n'est pas disponible, une erreur claire est levée plutôt qu'un résultat
de mauvaise qualité.
"""

from .translator import ollama_disponible, URL_OLLAMA, MODELE_OLLAMA


class ErreurResume(Exception):
    pass


def resumer_texte(texte: str, langue: str = "fr") -> str:
    if not texte.strip():
        raise ErreurResume("Texte vide, rien à résumer.")

    if not ollama_disponible():
        raise ErreurResume(
            "Le résumé nécessite Ollama, non détecté sur cette machine. "
            "Installe-le depuis https://ollama.com puis lance : ollama pull qwen3:7b"
        )

    import ollama
    client = ollama.Client(host=URL_OLLAMA)
    prompt = (
        f"Résume le texte suivant en {langue}, en 3 à 5 phrases claires et "
        f"concises, en gardant uniquement les idées principales. Réponds "
        f"uniquement avec le résumé, sans préambule ni commentaire :\n\n{texte}"
    )
    reponse = client.generate(model=MODELE_OLLAMA, prompt=prompt)
    return reponse.response.strip()