"""
Assemble la vidéo finale : vidéo d'origine (image) + nouvelle piste audio traduite.

Par défaut (`marquage=True`), incruste une mention visible "Kalima AI -
Powered by nOX-00" dans un coin de l'image, plus des métadonnées de
fichier explicites (titre, commentaire de divulgation IA, auteur).

Compromis assumé : incruster du texte dans l'image nécessite de
réencoder le flux vidéo (impossible avec un simple "-c:v copy" qui se
contente de copier les pixels tels quels). Le réencodage est fait en
qualité quasi sans perte (CRF 19) mais prend plus de temps que la
copie directe -- c'est le prix du marquage visible. Passe
`marquage=False` pour retrouver le comportement copie-directe si la
vitesse prime pour un usage donné.
"""

import subprocess
import os

TEXTE_MARQUAGE = "Kalima AI - Powered by nOX-00"
COMMENTAIRE_METADATA = (
    "Video doublee par intelligence artificielle (Kalima). "
    "Voix et traduction generees automatiquement. Powered by nOX-00."
)


class ErreurAssemblage(Exception):
    pass


def assembler_video_finale(chemin_video_originale: str, chemin_audio_traduit: str, chemin_sortie: str, marquage: bool = True) -> str:
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
    ]

    if marquage:
        filtre = (
            f"drawtext=text='{TEXTE_MARQUAGE}':fontcolor=white@0.7:fontsize=15:"
            f"x=w-tw-14:y=h-th-14:box=1:boxcolor=black@0.35:boxborderw=6"
        )
        commande += ["-vf", filtre, "-c:v", "libx264", "-preset", "fast", "-crf", "19"]
    else:
        commande += ["-c:v", "copy"]  # aucun réencodage vidéo -> rapide, sans perte

    commande += ["-c:a", "aac", "-b:a", "192k", "-shortest"]

    if marquage:
        commande += [
            "-metadata", "title=Kalima AI Creation",
            "-metadata", f"comment={COMMENTAIRE_METADATA}",
            "-metadata", "artist=nOX-00",
        ]

    commande += [chemin_sortie]

    resultat = subprocess.run(commande, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if resultat.returncode != 0:
        raise ErreurAssemblage(f"FFmpeg a échoué : {resultat.stderr.decode(errors='replace')}")

    return chemin_sortie