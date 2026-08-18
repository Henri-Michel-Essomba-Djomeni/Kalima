"""
Cache de transcription basé sur l'empreinte (hash) du fichier vidéo.

Si la même vidéo (identique au bit près) a déjà été transcrite
récemment -- par exemple en mode "transcription seule" hier, puis en
mode "doublage" aujourd'hui sur le même fichier -- on réutilise
directement le résultat au lieu de refaire tourner Whisper depuis
zéro. C'est l'étape la plus coûteuse du pipeline, donc le gain de
temps est réel dès qu'on enchaîne plusieurs modes sur une même vidéo.

Le cache expire automatiquement après quelques jours (réglable via la
variable d'environnement KALIMA_CACHE_JOURS) pour ne pas accumuler de
l'espace disque indéfiniment.
"""

import os
import sqlite3
import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Optional

from .transcriber import SegmentTranscrit

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHEMIN_DB = os.path.join(BASE_DIR, "jobs", "cache_transcriptions.db")
JOURS_EXPIRATION = int(os.environ.get("KALIMA_CACHE_JOURS", "7"))


def _init_db():
    os.makedirs(os.path.dirname(CHEMIN_DB), exist_ok=True)
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS cache_transcriptions ("
            "empreinte TEXT PRIMARY KEY, "
            "langue_detectee TEXT, "
            "segments_json TEXT NOT NULL, "
            "cree_le TEXT NOT NULL)"
        )


_init_db()


def calculer_empreinte(chemin_fichier: str) -> str:
    """
    Empreinte SHA-256 du contenu du fichier, calculée par blocs de 8 Mo
    pour ne jamais charger tout le fichier vidéo en mémoire d'un coup
    (important pour les fichiers volumineux).
    """
    hachage = hashlib.sha256()
    with open(chemin_fichier, "rb") as f:
        for bloc in iter(lambda: f.read(8 * 1024 * 1024), b""):
            hachage.update(bloc)
    return hachage.hexdigest()


def nettoyer_cache_expire():
    limite = (datetime.utcnow() - timedelta(days=JOURS_EXPIRATION)).isoformat()
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute("DELETE FROM cache_transcriptions WHERE cree_le < ?", (limite,))


def lire_cache(empreinte: str) -> Optional[List[SegmentTranscrit]]:
    nettoyer_cache_expire()
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute(
            "SELECT * FROM cache_transcriptions WHERE empreinte = ?", (empreinte,)
        ).fetchone()

    if not ligne:
        return None

    donnees = json.loads(ligne["segments_json"])
    return [
        SegmentTranscrit(
            debut=d["debut"], fin=d["fin"], texte=d["texte"],
            langue_detectee=d["langue_detectee"],
        )
        for d in donnees
    ]


def ecrire_cache(empreinte: str, segments: List[SegmentTranscrit]):
    if not segments:
        return
    donnees = [
        {"debut": s.debut, "fin": s.fin, "texte": s.texte, "langue_detectee": s.langue_detectee}
        for s in segments
    ]
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO cache_transcriptions "
            "(empreinte, langue_detectee, segments_json, cree_le) VALUES (?, ?, ?, ?)",
            (empreinte, segments[0].langue_detectee, json.dumps(donnees, ensure_ascii=False), datetime.utcnow().isoformat()),
        )