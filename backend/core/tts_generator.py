"""
Génération de voix (Text-to-Speech) avec edge-tts.

Pourquoi edge-tts plutôt que gTTS :
- Voix neuronales de bien meilleure qualité (pas robotique).
- Beaucoup de voix disponibles par langue, mais on en fixe UNE seule
  par langue cible dans VOIX_PAR_LANGUE pour garder une voix cohérente
  tout au long de la vidéo (jamais une voix humaine réelle clonée :
  ce sont des voix synthétiques génériques de Microsoft).
- Fonctionne aussi bien sur CPU que GPU (traitement dans le cloud),
  donc pas de dépendance au matériel de l'utilisateur.
- Support de la vitesse d'élocution (utile pour caler l'audio traduit
  sur la durée du segment vidéo d'origine).

Nécessite une connexion internet (c'est un service gratuit de Microsoft,
pas une clé API payante).
"""

import asyncio
import os
from typing import Optional
import edge_tts

# Une voix neutre et cohérente par langue. Modifiable/étendable facilement.
VOIX_PAR_LANGUE = {
    "fr": "fr-FR-HenriNeural",
    "en": "en-US-GuyNeural",
    "es": "es-ES-AlvaroNeural",
    "de": "de-DE-ConradNeural",
    "it": "it-IT-DiegoNeural",
    "pt": "pt-BR-AntonioNeural",
    "ar": "ar-SA-HamedNeural",
    "zh": "zh-CN-YunxiNeural",
    "ja": "ja-JP-KeitaNeural",
    "ru": "ru-RU-DmitryNeural",
}


class ErreurTTS(Exception):
    pass


async def _generer_async(texte: str, voix: str, chemin_sortie: str, taux_vitesse: str = "+0%"):
    communicate = edge_tts.Communicate(texte, voix, rate=taux_vitesse)
    await communicate.save(chemin_sortie)


def generer_voix(texte: str, langue: str, chemin_sortie: str, taux_vitesse: str = "+0%") -> str:
    """
    Génère un fichier audio à partir d'un texte.

    taux_vitesse: ex "+0%", "+15%", "-10%" -- utile pour ajuster la durée
                  de l'audio traduit à celle du segment vidéo d'origine.
    """
    if langue not in VOIX_PAR_LANGUE:
        raise ErreurTTS(f"Langue '{langue}' non supportée pour la voix. Dispo : {list(VOIX_PAR_LANGUE.keys())}")

    if not texte.strip():
        raise ErreurTTS("Texte vide, rien à synthétiser.")

    os.makedirs(os.path.dirname(chemin_sortie) or ".", exist_ok=True)
    voix = VOIX_PAR_LANGUE[langue]

    asyncio.run(_generer_async(texte, voix, chemin_sortie, taux_vitesse))
    return chemin_sortie


if __name__ == "__main__":
    generer_voix(
        "This is a test of the new voice generation system.",
        langue="en",
        chemin_sortie="test_voix.mp3",
    )
    print("Fichier test_voix.mp3 généré.")
