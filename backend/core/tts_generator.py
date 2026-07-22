"""
Génération de voix (Text-to-Speech) avec Kokoro-82M — licence Apache 2.0.

Kokoro est un système TTS neuronal 100 % local :
- Licence Apache 2.0 (poids et code), usage commercial sans restriction.
- 82M paramètres, fonctionne sur CPU (~3 GB RAM).
- 54 voix pré-définies dans 8 langues.
- Aucun appel réseau (modèle téléchargé une fois depuis HuggingFace).

Remplace l'ancien backend Piper TTS (archivé, fork GPL).
"""

import os
import wave
import numpy as np
from pathlib import Path
from typing import Optional

from kokoro import KPipeline


VOIX_KOKORO = {
    "fr": {"lang": "f", "voix": "ff_siwis"},
    "en": {"lang": "a", "voix": "am_adam"},
    "es": {"lang": "e", "voix": "ef_dora"},
    "it": {"lang": "i", "voix": "if_sara"},
    "pt": {"lang": "p", "voix": "pf_dora"},
    "ja": {"lang": "j", "voix": "jf_nezumi"},
    "zh": {"lang": "z", "voix": "zf_xiaobei"},
    "ko": {"lang": "k", "voix": "kf_youngmi"},
}

LANGUES_SUPPORTEES = list(VOIX_KOKORO.keys())


class ErreurTTS(Exception):
    pass


class GenerateurVoix:
    def __init__(self):
        self._pipelines: dict[str, KPipeline] = {}

    def _pipeline(self, langue: str) -> KPipeline:
        if langue not in self._pipelines:
            info = VOIX_KOKORO.get(langue)
            if info is None:
                raise ErreurTTS(
                    f"Langue '{langue}' non supportée. "
                    f"Supportées : {LANGUES_SUPPORTEES}"
                )
            self._pipelines[langue] = KPipeline(lang_code=info["lang"])
        return self._pipelines[langue]

    def generer(self, texte: str, langue: str, chemin_sortie: str, vitesse: float = 1.0) -> str:
        if not texte.strip():
            raise ErreurTTS("Texte vide, rien à synthétiser.")

        info = VOIX_KOKORO[langue]
        pipeline = self._pipeline(langue)

        morceaux = []
        for audio, _ in pipeline(texte, voice=info["voix"], speed=vitesse):
            morceaux.append(audio)

        if not morceaux:
            raise ErreurTTS("Aucun audio généré par Kokoro.")

        audio_complet = np.concatenate(morceaux)

        os.makedirs(os.path.dirname(chemin_sortie) or ".", exist_ok=True)
        with wave.open(chemin_sortie, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(24000)
            wf.writeframes((audio_complet * 32767).astype(np.int16).tobytes())

        return chemin_sortie


_GENERATEUR_VOIX: Optional[GenerateurVoix] = None


def generer_voix(
    texte: str,
    langue: str,
    chemin_sortie: str,
    taux_vitesse: str = "+0%",
) -> str:
    global _GENERATEUR_VOIX
    if _GENERATEUR_VOIX is None:
        _GENERATEUR_VOIX = GenerateurVoix()

    pourcentage = int(taux_vitesse.replace("+", "").replace("%", ""))
    vitesse = 1.0 + pourcentage / 100.0

    return _GENERATEUR_VOIX.generer(texte, langue, chemin_sortie, vitesse=vitesse)


if __name__ == "__main__":
    generer_voix(
        "This is a test of Kokoro TTS running locally.",
        langue="en",
        chemin_sortie="test_kokoro.wav",
    )
    print("Fichier test_kokoro.wav généré.")
