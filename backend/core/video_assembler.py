"""
Assemble la vidéo finale : vidéo d'origine (image) + nouvelle piste audio traduite.

Différence clé avec l'ancienne version : on ne réencode JAMAIS la vidéo.
L'ancien video_assembler.py rechargeait chaque chunk vidéo avec MoviePy et
les réencodait tous en les recollant -> lent, gourmand en RAM, et perte de
qualité à chaque réencodage. Ici on utilise ffmpeg avec "-c:v copy" : le flux
vidéo est copié tel quel, seul l'audio est remplacé. Résultat : quasi instantané
et zéro perte de qualité d'image, quelle que soit la taille du fichier.
"""

import subprocess
import os


class ErreurAssemblage(Exception):
    pass


def assembler_video_finale(chemin_video_originale: str, chemin_audio_traduit: str, chemin_sortie: str) -> str:
    if not os.path.exists(chemin_video_originale):
        raise ErreurAssemblage(f"Vidéo introuvable : {chemin_video_originale}")
    if not os.path.exists(chemin_audio_traduit):
        raise ErreurAssemblage(f"Audio introuvable : {chemin_audio_traduit}")

    os.makedirs(os.path.dirname(chemin_sortie) or ".", exist_ok=True)

    commande = [
        "ffmpeg", "-y",
        "-i", chemin_video_originale,
        "-i", chemin_audio_traduit,
        "-map", "0:v:0",       # image de la vidéo d'origine
        "-map", "1:a:0",       # audio du fichier traduit
        "-c:v", "copy",        # aucun réencodage vidéo -> rapide, sans perte
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        chemin_sortie,
    ]

    resultat = subprocess.run(commande, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if resultat.returncode != 0:
        raise ErreurAssemblage(f"FFmpeg a échoué : {resultat.stderr.decode(errors='replace')}")

    return chemin_sortie
