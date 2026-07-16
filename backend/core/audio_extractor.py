"""
Extraction audio depuis une vidéo, quelle que soit sa taille.

Contrairement à l'ancienne version qui découpait la vidéo en morceaux de
60 secondes (ce qui coupait les phrases en plein milieu et cassait la
transcription), ici on extrait UNE SEULE piste audio complète en WAV.
C'est ensuite Whisper (avec sa détection de silence intégrée) qui va
segmenter intelligemment la parole en phrases cohérentes.

FFmpeg gère très bien des fichiers volumineux car il traite le flux
sans jamais tout charger en mémoire d'un coup.
"""

import subprocess
import os


class ErreurExtraction(Exception):
    pass


def extraire_audio(chemin_video: str, chemin_audio_sortie: str) -> str:
    """
    Extrait la piste audio d'une vidéo vers un fichier WAV mono 16kHz,
    le format attendu par Whisper.

    Args:
        chemin_video: chemin vers le fichier vidéo source
        chemin_audio_sortie: chemin du .wav à générer

    Returns:
        Le chemin du fichier audio généré
    """
    if not os.path.exists(chemin_video):
        raise ErreurExtraction(f"Le fichier vidéo n'existe pas : {chemin_video}")

    os.makedirs(os.path.dirname(chemin_audio_sortie) or ".", exist_ok=True)

    commande = [
        "ffmpeg", "-y",
        "-i", chemin_video,
        "-vn",                  # pas de vidéo
        "-acodec", "pcm_s16le", # WAV brut, format attendu par Whisper
        "-ar", "16000",         # 16kHz, standard pour la reconnaissance vocale
        "-ac", "1",             # mono
        chemin_audio_sortie,
    ]

    resultat = subprocess.run(
        commande, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE
    )

    if resultat.returncode != 0:
        raise ErreurExtraction(
            f"FFmpeg a échoué : {resultat.stderr.decode(errors='replace')}"
        )

    return chemin_audio_sortie


def obtenir_duree_video(chemin_video: str) -> float:
    """Retourne la durée de la vidéo en secondes via ffprobe."""
    commande = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        chemin_video,
    ]
    resultat = subprocess.run(commande, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if resultat.returncode != 0:
        raise ErreurExtraction(
            f"Impossible de lire la durée : {resultat.stderr.decode(errors='replace')}"
        )
    return float(resultat.stdout.decode().strip())
