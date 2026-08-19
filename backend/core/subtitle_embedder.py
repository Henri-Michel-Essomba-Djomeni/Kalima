"""
Incruste des sous-titres (piste texte sélectionnable, pas gravée dans
l'image) dans une vidéo SANS jamais toucher à l'audio d'origine --
c'est le principe même du mode "sous-titres seuls".

Par défaut (`marquage=True`), incruste aussi une mention visible
"Kalima AI - Powered by nOX-00" dans un coin de l'image, plus des
métadonnées de fichier. Ça implique de réencoder l'image (impossible
de dessiner du texte sur un flux simplement copié), mais l'audio,
lui, reste toujours une copie directe -- jamais réencodé, jamais
modifié, quel que soit le réglage de marquage.
"""

import subprocess
import os

from .video_assembler import TEXTE_MARQUAGE, COMMENTAIRE_METADATA


class ErreurIncrustation(Exception):
    pass


def incruster_sous_titres(chemin_video: str, chemin_srt: str, chemin_sortie: str, marquage: bool = True) -> str:
    if not os.path.exists(chemin_video):
        raise ErreurIncrustation(f"Vidéo introuvable : {chemin_video}")
    if not os.path.exists(chemin_srt):
        raise ErreurIncrustation(f"Sous-titres introuvables : {chemin_srt}")

    os.makedirs(os.path.dirname(chemin_sortie) or ".", exist_ok=True)

    commande = [
        "ffmpeg", "-y",
        "-i", chemin_video,
        "-i", chemin_srt,
        "-map", "0:v:0", "-map", "0:a:0", "-map", "1:0",
    ]

    if marquage:
        filtre = (
            f"drawtext=text='{TEXTE_MARQUAGE}':fontcolor=white@0.7:fontsize=15:"
            f"x=w-tw-14:y=h-th-14:box=1:boxcolor=black@0.35:boxborderw=6"
        )
        commande += ["-vf", filtre, "-c:v", "libx264", "-preset", "fast", "-crf", "19"]
    else:
        commande += ["-c:v", "copy"]  # image jamais réencodée

    commande += ["-c:a", "copy"]      # audio jamais touché -- c'est le point clé, dans tous les cas
    commande += ["-c:s", "mov_text", "-metadata:s:s:0", "language=und"]

    if marquage:
        commande += [
            "-metadata", "title=Kalima AI Creation",
            "-metadata", f"comment={COMMENTAIRE_METADATA}",
            "-metadata", "artist=nOX-00",
        ]

    commande += [chemin_sortie]

    resultat = subprocess.run(commande, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    if resultat.returncode != 0:
        raise ErreurIncrustation(f"FFmpeg a échoué : {resultat.stderr.decode(errors='replace')}")

    return chemin_sortie