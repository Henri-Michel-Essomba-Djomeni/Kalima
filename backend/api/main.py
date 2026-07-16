"""
API FastAPI pour piloter le pipeline de traduction vidéo depuis un navigateur.

Endpoints :
- POST /api/traduire        : upload d'une vidéo + langues -> retourne un job_id
- GET  /api/statut/{job_id} : progression en temps réel du job
- GET  /api/telecharger/{job_id} : télécharge la vidéo finale une fois terminée
- GET  /api/langues         : liste des langues supportées
"""

import os
import shutil
import threading
import sys

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import PipelineTraduction, ProgressionEtape
from core.translator import CODES_LANGUES_NLLB
from api.job_manager import creer_job, obtenir_job, mettre_a_jour_job, StatutJob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOSSIER_UPLOADS = os.path.join(BASE_DIR, "uploads")
DOSSIER_OUTPUTS = os.path.join(BASE_DIR, "outputs")
os.makedirs(DOSSIER_UPLOADS, exist_ok=True)
os.makedirs(DOSSIER_OUTPUTS, exist_ok=True)

app = FastAPI(title="VideoDubber API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Le pipeline charge des modèles lourds (Whisper, NLLB) : on le garde en
# mémoire une seule fois pour tous les jobs plutôt que de tout recharger
# à chaque requête, ce qui prendrait plusieurs minutes à chaque fois.
_pipeline = PipelineTraduction(taille_modele_whisper="medium")


def _executer_job_en_arriere_plan(job_id: str, chemin_video: str, langue_source: str, langue_cible: str):
    chemin_sortie = os.path.join(DOSSIER_OUTPUTS, f"{job_id}.mp4")

    def on_progress(p: ProgressionEtape):
        mettre_a_jour_job(
            job_id,
            statut=StatutJob.EN_COURS,
            etape=p.etape,
            pourcentage_etape=p.pourcentage,
            message=p.message,
        )

    try:
        _pipeline.executer(
            chemin_video=chemin_video,
            langue_source=langue_source,
            langue_cible=langue_cible,
            chemin_sortie=chemin_sortie,
            on_progress=on_progress,
        )
        mettre_a_jour_job(
            job_id,
            statut=StatutJob.TERMINE,
            chemin_video_sortie=chemin_sortie,
            message="Traduction terminée.",
        )
    except Exception as e:
        mettre_a_jour_job(job_id, statut=StatutJob.ERREUR, erreur=str(e))
    finally:
        # Nettoyage de la vidéo uploadée, plus besoin une fois le job fini
        if os.path.exists(chemin_video):
            os.remove(chemin_video)


@app.get("/api/langues")
def lister_langues():
    return {"langues": sorted(CODES_LANGUES_NLLB.keys())}


@app.post("/api/traduire")
async def lancer_traduction(
    fichier: UploadFile = File(...),
    langue_source: str = Form(...),
    langue_cible: str = Form(...),
):
    if langue_source not in CODES_LANGUES_NLLB or langue_cible not in CODES_LANGUES_NLLB:
        raise HTTPException(400, "Langue non supportée.")

    job = creer_job()
    chemin_video = os.path.join(DOSSIER_UPLOADS, f"{job.id}_{fichier.filename}")

    # Écriture par blocs pour ne pas charger toute la vidéo en mémoire
    # d'un coup, important pour les fichiers volumineux.
    with open(chemin_video, "wb") as f:
        while True:
            morceau = await fichier.read(1024 * 1024)  # 1 Mo par bloc
            if not morceau:
                break
            f.write(morceau)

    thread = threading.Thread(
        target=_executer_job_en_arriere_plan,
        args=(job.id, chemin_video, langue_source, langue_cible),
        daemon=True,
    )
    thread.start()

    return {"job_id": job.id}


@app.get("/api/statut/{job_id}")
def statut_job(job_id: str):
    job = obtenir_job(job_id)
    if job is None:
        raise HTTPException(404, "Job introuvable.")
    return {
        "statut": job.statut,
        "etape": job.etape,
        "pourcentage_etape": job.pourcentage_etape,
        "message": job.message,
        "erreur": job.erreur,
    }


@app.get("/api/telecharger/{job_id}")
def telecharger(job_id: str):
    job = obtenir_job(job_id)
    if job is None or job.statut != StatutJob.TERMINE or not job.chemin_video_sortie:
        raise HTTPException(404, "Vidéo non disponible.")
    return FileResponse(
        job.chemin_video_sortie,
        media_type="video/mp4",
        filename="video_traduite.mp4",
    )


# Sert le frontend statique (index.html, etc.)
chemin_frontend = os.path.join(BASE_DIR, "frontend")
if os.path.isdir(chemin_frontend):
    app.mount("/", StaticFiles(directory=chemin_frontend, html=True), name="frontend")
