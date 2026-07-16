"""
Gestion des jobs de traduction en cours.

Chaque upload vidéo devient un "job" avec un identifiant unique. On garde
son état (en attente, en cours, terminé, erreur) et sa progression en
mémoire, pour que le frontend puisse interroger régulièrement l'API et
afficher une barre de progression sans websocket compliqué.

Pour une vraie mise en prod avec plusieurs utilisateurs simultanés, on
remplacerait ce stockage en mémoire par Redis ou une base de données,
mais pour un usage personnel/local, un dictionnaire en mémoire suffit
largement et reste simple à maintenir.
"""

import uuid
import threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Optional


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


# Verrou pour éviter les accès concurrents corrompus au dictionnaire de jobs
_verrou = threading.Lock()
_jobs: Dict[str, Job] = {}


def creer_job() -> Job:
    job_id = str(uuid.uuid4())
    job = Job(id=job_id)
    with _verrou:
        _jobs[job_id] = job
    return job


def obtenir_job(job_id: str) -> Optional[Job]:
    with _verrou:
        return _jobs.get(job_id)


def mettre_a_jour_job(job_id: str, **kwargs) -> None:
    with _verrou:
        job = _jobs.get(job_id)
        if job is None:
            return
        for cle, valeur in kwargs.items():
            setattr(job, cle, valeur)
