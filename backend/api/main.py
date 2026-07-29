import os
import threading
import sys
import secrets
import base64

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import PipelineTraduction, ProgressionEtape
from core.translator import CODES_LANGUES
from core.voice_cloner import LANGUES_CLONABLES
from core.srt_exporter import segments_vers_srt, segments_vers_vtt, segments_vers_texte, charger_transcription
from api.job_manager import creer_job, obtenir_job, mettre_a_jour_job, lister_jobs, StatutJob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOSSIER_UPLOADS = os.path.join(BASE_DIR, "uploads")
DOSSIER_OUTPUTS = os.path.join(BASE_DIR, "outputs")
os.makedirs(DOSSIER_UPLOADS, exist_ok=True)
os.makedirs(DOSSIER_OUTPUTS, exist_ok=True)

# Identifiants d'accès -- à changer via variables d'environnement avant
# d'exposer le serveur publiquement (tunnel, port forwarding, etc.).
UTILISATEUR = os.environ.get("KALIMA_USER", "admin")
MOT_DE_PASSE = os.environ.get("KALIMA_PASS", "changemoi")

app = FastAPI(title="Kalima API")


class AuthentificationBasique(BaseHTTPMiddleware):
    """Protège toutes les routes par mot de passe (HTTP Basic Auth)."""
    async def dispatch(self, request: Request, call_next):
        entete = request.headers.get("Authorization")
        if entete and entete.startswith("Basic "):
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

_pipeline = PipelineTraduction(taille_modele_whisper="medium")


def _executer_job_en_arriere_plan(
    job_id: str, chemin_video: str, langue_source: str, langue_cible: str, cloner_voix: bool = False
):
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
        if os.path.exists(chemin_video):
            os.remove(chemin_video)


@app.get("/api/langues")
def lister_langues():
    return {"langues": sorted(CODES_LANGUES.keys())}


@app.get("/api/langues-clonables")
def lister_langues_clonables():
    return {"langues": sorted(LANGUES_CLONABLES.keys())}


@app.get("/api/jobs")
def lister_tous_les_jobs():
    return {"jobs": [{
        "id": j.id,
        "statut": j.statut,
        "etape": j.etape,
        "pourcentage_etape": j.pourcentage_etape,
        "message": j.message,
        "langue_source": j.langue_source,
        "langue_cible": j.langue_cible,
        "cree_le": j.cree_le,
    } for j in lister_jobs()]}


@app.post("/api/traduire")
async def lancer_traduction(
    fichier: UploadFile = File(...),
    langue_source: str = Form(...),
    langue_cible: str = Form(...),
    cloner_voix: bool = Form(False),
):
    if langue_source not in CODES_LANGUES or langue_cible not in CODES_LANGUES:
        raise HTTPException(400, "Langue non supportée.")

    job = creer_job(langue_source=langue_source, langue_cible=langue_cible)
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


@app.get("/api/sous-titres/{job_id}")
def sous_titres(job_id: str, format: str = Query("srt", pattern="^(srt|vtt)$")):
    job = obtenir_job(job_id)
    if job is None or job.statut != StatutJob.TERMINE or not job.chemin_video_sortie:
        raise HTTPException(404, "Job introuvable ou pas encore terminé.")

    chemin_json = job.chemin_video_sortie.replace(".mp4", "_transcription.json")
    segments = charger_transcription(chemin_json)
    if segments is None:
        raise HTTPException(404, "Transcription non disponible.")

    if format == "srt":
        contenu = segments_vers_srt(segments)
        media_type = "text/plain"
        filename = f"sous-titres_{job_id}.srt"
    else:
        contenu = segments_vers_vtt(segments)
        media_type = "text/vtt"
        filename = f"sous-titres_{job_id}.vtt"

    return PlainTextResponse(content=contenu, media_type=media_type,
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.get("/api/transcription/{job_id}")
def transcription(job_id: str, format: str = Query("txt", pattern="^(txt|json)$")):
    job = obtenir_job(job_id)
    if job is None or job.statut != StatutJob.TERMINE or not job.chemin_video_sortie:
        raise HTTPException(404, "Job introuvable ou pas encore terminé.")

    chemin_json = job.chemin_video_sortie.replace(".mp4", "_transcription.json")
    segments = charger_transcription(chemin_json)
    if segments is None:
        raise HTTPException(404, "Transcription non disponible.")

    if format == "json":
        contenu = open(chemin_json, "r", encoding="utf-8").read()
        media_type = "application/json"
        filename = f"transcription_{job_id}.json"
    else:
        contenu = segments_vers_texte(segments)
        media_type = "text/plain"
        filename = f"transcription_{job_id}.txt"

    return PlainTextResponse(content=contenu, media_type=media_type,
                             headers={"Content-Disposition": f"attachment; filename={filename}"})


@app.post("/api/tts")
async def tts_texte(texte: str = Form(...), langue: str = Form("fr")):
    from core.tts_generator import generer_voix

    if not texte.strip():
        raise HTTPException(400, "Texte vide.")

    dossier = os.path.join(BASE_DIR, "outputs", "tts_temp")
    os.makedirs(dossier, exist_ok=True)
    chemin = os.path.join(dossier, f"tts_{abs(hash(texte))}.wav")

    try:
        generer_voix(texte, langue, chemin)
    except Exception as e:
        raise HTTPException(500, f"Erreur TTS : {e}")

    return FileResponse(chemin, media_type="audio/wav", filename="audio.wav")


chemin_frontend = os.path.join(BASE_DIR, "frontend")
if os.path.isdir(chemin_frontend):
    app.mount("/", StaticFiles(directory=chemin_frontend, html=True), name="frontend")
