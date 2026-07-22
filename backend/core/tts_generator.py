"""
Génération de voix (Text-to-Speech) avec Piper TTS — licence MIT.

Piper est un système TTS neuronal 100 % local :
- Licence MIT (voix et code), usage commercial sans restriction.
- Aucun appel réseau, aucune dépendance cloud.
- Fonctionne sur CPU, plus rapide que le temps réel sur un Raspberry Pi.
- Chaque langue a son propre modèle vocal (ONNX, téléchargé une seule fois).

Les modèles sont téléchargés automatiquement depuis HuggingFace
(https://huggingface.co/rhasspy/piper-voices) au premier appel.
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Optional

from pydub import AudioSegment


# Voix Piper par langue. Chaque entrée pointe vers un modèle ONNX
# disponible dans le dossier DOSSIER_MODELES.
# Source : https://github.com/rhasspy/piper?tab=readme-ov-file#voices
VOIX_PAR_LANGUE = {
    "fr": "fr_FR-mls-medium",
    "en": "en_US-ryan-medium",
    "es": "es_ES-mls-medium",
    "de": "de_DE-thorsten-medium",
    "it": "it_IT-paola-medium",
    "pt": "pt_BR-edresson-medium",
    "ru": "ru_RU-irina-medium",
    "zh": "zh_CN-huihui-medium",
    "ar": "ar_AE-hassan-medium",
    "ja": "ja_JP-tanjiro-medium",
}

DOSSIER_PROJET = Path(__file__).resolve().parent.parent.parent
DOSSIER_VOIX = DOSSIER_PROJET / "voices"

_HF_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


class ErreurTTS(Exception):
    pass


def _trouver_piper() -> Optional[str]:
    """Cherche le binaire piper dans PATH ou dans ./piper/ du projet."""
    essais = [
        "piper",
        "piper.exe",
        str(DOSSIER_PROJET / "piper" / "piper"),
        str(DOSSIER_PROJET / "piper" / "piper.exe"),
    ]
    for chemin in essais:
        try:
            subprocess.run([chemin, "--help"], capture_output=True, check=False)
            return chemin
        except FileNotFoundError:
            continue
    return None


def _telecharger_modele(nom_voix: str) -> Path:
    """
    Télécharge le modèle ONNX + config JSON depuis HuggingFace
    si pas déjà présent dans DOSSIER_VOIX.
    """
    voix_repertoire = DOSSIER_VOIX / nom_voix
    voix_repertoire.mkdir(parents=True, exist_ok=True)

    chemin_onnx = voix_repertoire / f"{nom_voix}.onnx"
    chemin_json = voix_repertoire / f"{nom_voix}.json"

    if chemin_onnx.exists() and chemin_json.exists():
        return chemin_onnx

    import requests

    print(f"[+] Téléchargement du modèle vocal '{nom_voix}'...")
    for nom_fichier in [f"{nom_voix}.onnx", f"{nom_voix}.json"]:
        url = f"{_HF_BASE}/{nom_voix}/fr_FR/mls/medium/{nom_fichier}"
        url = f"{_HF_BASE}/{nom_voix}/{nom_fichier}"
        cible = voix_repertoire / nom_fichier
        rep = requests.get(url, timeout=120)
        if rep.status_code != 200:
            # Tentative avec chemin alternatif (certaines voix sont organisées différemment)
            # Format: rhasspy/piper-voices/{langue}/{nom_voix}
            langue = nom_voix.split("_")[0]
            url_alt = f"{_HF_BASE}/{langue}/{nom_voix}/{nom_fichier}"
            rep = requests.get(url_alt, timeout=120)
            if rep.status_code != 200:
                raise ErreurTTS(
                    f"Impossible de télécharger le modèle '{nom_voix}' "
                    f"(HTTP {rep.status_code}). Vérifiez votre connexion."
                )
        with open(cible, "wb") as f:
            f.write(rep.content)

    return chemin_onnx


def generer_voix(
    texte: str,
    langue: str,
    chemin_sortie: str,
    taux_vitesse: str = "+0%",
) -> str:
    """
    Génère un fichier audio WAV à partir d'un texte via Piper TTS.

    Args:
        texte: texte à synthétiser
        langue: code ISO (fr, en, es, de, it, pt, ru, zh, ar, ja)
        chemin_sortie: chemin du fichier .wav à générer
        taux_vitesse: ex "+0%", "+15%", "-10%" — ajustement appliqué
                      après génération via pydub (changement de sample rate)

    Returns:
        Le chemin du fichier audio généré
    """
    if langue not in VOIX_PAR_LANGUE:
        raise ErreurTTS(
            f"Langue '{langue}' non supportée. "
            f"Langues disponibles : {list(VOIX_PAR_LANGUE.keys())}"
        )

    if not texte.strip():
        raise ErreurTTS("Texte vide, rien à synthétiser.")

    os.makedirs(os.path.dirname(chemin_sortie) or ".", exist_ok=True)

    nom_voix = VOIX_PAR_LANGUE[langue]
    chemin_modele = _telecharger_modele(nom_voix)
    chemin_piper = _trouver_piper()

    if chemin_piper is None:
        raise ErreurTTS(
            "Binaire Piper introuvable. "
            "Téléchargez-le depuis https://github.com/rhasspy/piper/releases "
            "et placez-le dans le PATH ou dans le dossier 'piper/' du projet."
        )

    # Piper écrit sur stdout par défaut, on redirige vers un fichier WAV
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        chemin_temp = tmp.name

    try:
        cmd = [
            chemin_piper,
            "--model", str(chemin_modele),
            "--output-file", chemin_temp,
        ]
        proc = subprocess.run(
            cmd,
            input=texte.encode("utf-8"),
            capture_output=True,
            timeout=120,
        )
        if proc.returncode != 0:
            raise ErreurTTS(
                f"Piper a échoué : {proc.stderr.decode(errors='replace')}"
            )

        # Ajustement de la vitesse via pydub si demandé
        if taux_vitesse != "+0%":
            pourcentage = int(taux_vitesse.replace("+", "").replace("%", ""))
            ratio = 1.0 + pourcentage / 100.0
            audio = AudioSegment.from_file(chemin_temp)
            # Changer le frame rate pour simuler l'accélération/ralentissement
            # tout en préservant la hauteur tonale n'est pas parfait,
            # mais pour de petites variations (< 30%) c'est acceptable.
            nouveau_taux = int(audio.frame_rate * ratio)
            audio = audio._spawn(
                audio.raw_data,
                overrides={"frame_rate": nouveau_taux},
            )
            audio = audio.set_frame_rate(audio.frame_rate)
            audio.export(chemin_sortie, format="wav")
        else:
            # Copie simple
            audio = AudioSegment.from_file(chemin_temp)
            audio.export(chemin_sortie, format="wav")

    finally:
        if os.path.exists(chemin_temp):
            os.remove(chemin_temp)

    return chemin_sortie


def _generer_multiple_vitesse(
    texte: str,
    langue: str,
    dossier_temp: str,
    index: int,
    fenetre_ms: float,
    marge_max: float = 1.4,
) -> str:
    """
    Génère un segment audio et l'exporte en WAV.
    Si la durée dépasse la fenêtre disponible, régénère avec
    une vitesse accélérée.
    """
    chemin_sortie = os.path.join(dossier_temp, f"seg_{index:04d}.wav")
    generer_voix(texte, langue, chemin_sortie)
    duree = len(AudioSegment.from_file(chemin_sortie))

    if duree > fenetre_ms > 0:
        ratio = duree / fenetre_ms
        ratio = min(ratio, marge_max)
        pct = int((ratio - 1) * 100)
        generer_voix(texte, langue, chemin_sortie, taux_vitesse=f"+{pct}%")

    return chemin_sortie


if __name__ == "__main__":
    generer_voix(
        "This is a test of Piper TTS running locally.",
        langue="en",
        chemin_sortie="test_piper.wav",
    )
    print("Fichier test_piper.wav généré.")
