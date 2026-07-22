"""
Gestion des jobs de traduction avec persistance SQLite.

Remplace le dictionnaire en mémoire pour que les jobs survivent
au redémarrage du serveur. Utilise sqlite3 (stdlib Python) —
zéro dépendance externe.
"""

import uuid
import sqlite3
import os
import threading
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from typing import Optional


DOSSIER_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "jobs",
)
os.makedirs(DOSSIER_DB, exist_ok=True)
CHEMIN_DB = os.path.join(DOSSIER_DB, "jobs.db")


class StatutJob(str, Enum):
    EN_ATTENTE = "en_attente"
    EN_COURS = "en_cours"
    TERMINE = "termine"
    ERREUR = "erreur"


@dataclass
class Job:
    id: str
    statut: StatutJob = StatutJob.EN_ATTENTE
    etape: str = ""
    pourcentage_etape: float = 0.0
    message: str = ""
    chemin_video_sortie: Optional[str] = None
    erreur: Optional[str] = None
    langue_source: str = ""
    langue_cible: str = ""
    cree_le: str = ""


_verrou = threading.Lock()


def _init_db():
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS jobs ("
            "id TEXT PRIMARY KEY, "
            "statut TEXT NOT NULL DEFAULT 'en_attente', "
            "etape TEXT DEFAULT '', "
            "pourcentage_etape REAL DEFAULT 0.0, "
            "message TEXT DEFAULT '', "
            "chemin_video_sortie TEXT, "
            "erreur TEXT, "
            "langue_source TEXT DEFAULT '', "
            "langue_cible TEXT DEFAULT '', "
            "cree_le TEXT NOT NULL)"
        )


_init_db()


def creer_job(langue_source: str = "", langue_cible: str = "") -> Job:
    job_id = str(uuid.uuid4())
    maintenant = datetime.utcnow().isoformat()
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "INSERT INTO jobs (id, statut, langue_source, langue_cible, cree_le) "
            "VALUES (?, ?, ?, ?, ?)",
            (job_id, StatutJob.EN_ATTENTE.value, langue_source, langue_cible, maintenant),
        )
    return Job(
        id=job_id,
        statut=StatutJob.EN_ATTENTE,
        langue_source=langue_source,
        langue_cible=langue_cible,
        cree_le=maintenant,
    )


def obtenir_job(job_id: str) -> Optional[Job]:
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if ligne is None:
        return None
    return Job(
        id=ligne["id"],
        statut=StatutJob(ligne["statut"]),
        etape=ligne["etape"],
        pourcentage_etape=ligne["pourcentage_etape"],
        message=ligne["message"],
        chemin_video_sortie=ligne["chemin_video_sortie"],
        erreur=ligne["erreur"],
        langue_source=ligne["langue_source"],
        langue_cible=ligne["langue_cible"],
        cree_le=ligne["cree_le"],
    )


def mettre_a_jour_job(job_id: str, **kwargs) -> None:
    champs = []
    valeurs = []
    for cle, valeur in kwargs.items():
        champs.append(f"{cle} = ?")
        if isinstance(valeur, Enum):
            valeur = valeur.value
        valeurs.append(valeur)
    valeurs.append(job_id)
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            f"UPDATE jobs SET {', '.join(champs)} WHERE id = ?",
            valeurs,
        )


def lister_jobs(limite: int = 20) -> list[Job]:
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        lignes = conn.execute(
            "SELECT * FROM jobs ORDER BY cree_le DESC LIMIT ?", (limite,)
        ).fetchall()
    return [
        Job(
            id=l["id"],
            statut=StatutJob(l["statut"]),
            etape=l["etape"],
            pourcentage_etape=l["pourcentage_etape"],
            message=l["message"],
            chemin_video_sortie=l["chemin_video_sortie"],
            erreur=l["erreur"],
            langue_source=l["langue_source"],
            langue_cible=l["langue_cible"],
            cree_le=l["cree_le"],
        )
        for l in lignes
    ]
