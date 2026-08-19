"""
Téléchargement d'une vidéo depuis un lien YouTube (ou toute autre
plateforme supportée par yt-dlp), pour l'utiliser ensuite exactement
comme un fichier uploadé dans le reste du pipeline.

Rappel important : tu dois avoir les droits sur le contenu que tu
traites (vidéo qui t'appartient, domaine public, licence libre...).
Ce module télécharge techniquement n'importe quel lien valide, mais ne
vérifie ni ne garantit aucune autorisation d'usage -- cette
responsabilité reste la tienne.
"""

import os

try:
    import yt_dlp
except ImportError:
    yt_dlp = None


class ErreurTelechargement(Exception):
    pass


def telecharger_video(url: str, dossier_sortie: str, nom_base: str) -> str:
    """
    Télécharge la vidéo depuis `url` dans `dossier_sortie`, nommée
    `nom_base.<extension>`. Retourne le chemin du fichier téléchargé.
    """
    if yt_dlp is None:
        raise ErreurTelechargement(
            "yt-dlp n'est pas installé. Lance : pip install yt-dlp"
        )

    os.makedirs(dossier_sortie, exist_ok=True)
    chemin_modele = os.path.join(dossier_sortie, f"{nom_base}.%(ext)s")

    options = {
        "format": "mp4/bestvideo+bestaudio/best",
        "merge_output_format": "mp4",
        "outtmpl": chemin_modele,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "max_filesize": 3 * 1024 * 1024 * 1024,  # 3 Go, cohérent avec la limite de l'app
    }

    try:
        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)
            chemin = ydl.prepare_filename(info)
            # yt-dlp peut changer l'extension finale après fusion audio/vidéo
            base_sans_ext = os.path.splitext(chemin)[0]
            chemin_mp4 = base_sans_ext + ".mp4"
            if os.path.exists(chemin_mp4):
                return chemin_mp4
            if os.path.exists(chemin):
                return chemin
            for ext in ("mkv", "webm"):
                candidat = f"{base_sans_ext}.{ext}"
                if os.path.exists(candidat):
                    return candidat
        raise ErreurTelechargement("Téléchargement terminé mais fichier introuvable sur le disque.")
    except ErreurTelechargement:
        raise
    except Exception as e:
        raise ErreurTelechargement(f"Impossible de télécharger cette vidéo : {e}")