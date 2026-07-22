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
import secrets

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import PipelineTraduction, ProgressionEtape
from core.translator import CODES_LANGUES_NLLB
from core.voice_cloner import LANGUES_CLONABLES
from api.job_manager import creer_job, obtenir_job, mettre_a_jour_job, StatutJob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOSSIER_UPLOADS = os.path.join(BASE_DIR, "uploads")
DOSSIER_OUTPUTS = os.path.join(BASE_DIR, "outputs")
os.makedirs(DOSSIER_UPLOADS, exist_ok=True)
os.makedirs(DOSSIER_OUTPUTS, exist_ok=True)

# Identifiants d'accès -- à changer via variables d'environnement avant
# d'exposer le serveur publiquement (tunnel, port forwarding, etc.).
# Sans ça, n'importe qui tombant sur l'URL pourrait utiliser ton app et
# faire tourner ton CPU/GPU à ta place.
UTILISATEUR = os.environ.get("KALIMA_USER", "admin")
MOT_DE_PASSE = os.environ.get("KALIMA_PASS", "changemoi")

app = FastAPI(title="Kalima API")


class AuthentificationBasique(BaseHTTPMiddleware):
    """
    Protège toutes les routes par mot de passe (HTTP Basic Auth).

    Nécessaire dès que le serveur est accessible depuis l'extérieur (via
    un tunnel type Cloudflare/ngrok, ou une redirection de port) : sans
    ça, l'URL publique serait utilisable par n'importe qui.
    """
    async def dispatch(self, request: Request, call_next):
        entete = request.headers.get("Authorization")
        if entete and entete.startswith("Basic "):
            import base64
            try:
                decode = base64.b64decode(entete[6:]).decode()
                utilisateur, _, mdp = decode.partition(":")
                if secrets.compare_digest(utilisateur, UTILISATEUR) and secrets.compare_digest(mdp, MOT_DE_PASSE):
                    return await call_next(request)
            except Exception:
                pass
        return JSONResponse(
            {"detail": "Authentification requise."},
            status_code=401,
            headers={"WWW-Authenticate": "Basic realm=\"Kalima\""},
        )


app.add_middleware(AuthentificationBasique)

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


def _executer_job_en_arriere_plan(job_id: str, chemin_video: str, langue_source: str, langue_cible: str, cloner_voix: bool = False):
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
            cloner_voix=cloner_voix,
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


@app.get("/api/langues-clonables")
def lister_langues_clonables():
    return {"langues": sorted(LANGUES_CLONABLES.keys())}


@app.post("/api/traduire")
async def lancer_traduction(
    fichier: UploadFile = File(...),
    langue_source: str = Form(...),
    langue_cible: str = Form(...),
    cloner_voix: bool = Form(False),
):
    if langue_source not in CODES_LANGUES_NLLB or langue_cible not in CODES_LANGUES_NLLB:
        raise HTTPException(400, "Langue non supportée.")

    job = creer_job()
    chemin_video = os.path.join(DOSSIER_UPLOADS, f"{job.id}_{fichier.filename}")

    with open(chemin_video, "wb") as f:
        while True:
            morceau = await fichier.read(1024 * 1024)
            if not morceau:
                break
            f.write(morceau)

    thread = threading.Thread(
        target=_executer_job_en_arriere_plan,
        args=(job.id, chemin_video, langue_source, langue_cible, cloner_voix),
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
