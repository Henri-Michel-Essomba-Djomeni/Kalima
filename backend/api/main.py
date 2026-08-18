import os
import threading
import sys
import secrets
import hashlib
import asyncio

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, Request
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse, HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pipeline import PipelineTraduction, ProgressionEtape
from core.translator import CODES_LANGUES
from core.voice_cloner import LANGUES_CLONABLES
from core.srt_exporter import segments_vers_srt, segments_vers_vtt, segments_vers_texte, charger_transcription
from core.youtube_downloader import telecharger_video, ErreurTelechargement
from api.job_manager import creer_job, obtenir_job, mettre_a_jour_job, lister_jobs, StatutJob

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DOSSIER_UPLOADS = os.path.join(BASE_DIR, "uploads")
DOSSIER_OUTPUTS = os.path.join(BASE_DIR, "outputs")
DOSSIER_FRONTEND = os.path.join(BASE_DIR, "frontend")
os.makedirs(DOSSIER_UPLOADS, exist_ok=True)
os.makedirs(DOSSIER_OUTPUTS, exist_ok=True)

# Identifiants d'accès -- à changer via variables d'environnement avant
# d'exposer le serveur publiquement (tunnel, port forwarding, etc.).
# Attention : ces variables ne survivent pas d'une fenêtre de terminal à
# l'autre (elles sont propres à la session PowerShell qui les a définies).
# Si tu les redéfinis puis ouvres un nouveau terminal pour lancer uvicorn,
# les valeurs par défaut ci-dessous seront utilisées à la place.
UTILISATEUR = os.environ.get("KALIMA_USER", "admin")
MOT_DE_PASSE = os.environ.get("KALIMA_PASS", "changemoi")

# Jeton de session : dérivé des identifiants, régénéré si tu changes le
# mot de passe (donc toute session ouverte avec l'ancien mot de passe est
# automatiquement invalidée). Suffisant pour une protection d'accès
# personnelle/petite échelle -- pas une architecture d'auth "entreprise".
_JETON_SESSION = hashlib.sha256(f"{UTILISATEUR}:{MOT_DE_PASSE}".encode()).hexdigest()
NOM_COOKIE = "kalima_session"
DUREE_SESSION_SECONDES = 30 * 24 * 3600  # 30 jours

CHEMINS_PUBLICS = {"/login", "/api/login", "/favicon.ico"}

app = FastAPI(title="Kalima API")


class AuthentificationSession(BaseHTTPMiddleware):
    """
    Protège toutes les routes sauf /login (page + endpoint) via un cookie
    de session. Les requêtes API sans session valide reçoivent un 401 JSON
    (le frontend redirige alors vers /login) ; les requêtes de page reçoivent
    directement une redirection HTTP vers /login.
    """
    async def dispatch(self, request: Request, call_next):
        if request.url.path in CHEMINS_PUBLICS:
            return await call_next(request)

        cookie = request.cookies.get(NOM_COOKIE)
        if cookie and secrets.compare_digest(cookie, _JETON_SESSION):
            return await call_next(request)

        if request.url.path.startswith("/api/"):
            return JSONResponse({"detail": "Session expirée ou absente."}, status_code=401)
        return RedirectResponse(url="/login", status_code=307)


app.add_middleware(AuthentificationSession)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/login")
def page_connexion():
    chemin = os.path.join(DOSSIER_FRONTEND, "login.html")
    return HTMLResponse(open(chemin, encoding="utf-8").read())


@app.post("/api/login")
async def connexion(utilisateur: str = Form(...), mot_de_passe: str = Form(...)):
    if secrets.compare_digest(utilisateur, UTILISATEUR) and secrets.compare_digest(mot_de_passe, MOT_DE_PASSE):
        reponse = JSONResponse({"ok": True})
        reponse.set_cookie(
            NOM_COOKIE, _JETON_SESSION,
            max_age=DUREE_SESSION_SECONDES, httponly=True, samesite="lax",
        )
        return reponse
    # Petit délai pour ralentir le bruteforce naïf, sans bloquer le reste
    # du serveur pendant ce temps (sleep asynchrone, pas synchrone).
    await asyncio.sleep(0.6)
    raise HTTPException(401, "Identifiants incorrects.")


@app.get("/api/logout")
def deconnexion():
    reponse = RedirectResponse(url="/login")
    reponse.delete_cookie(NOM_COOKIE, path="/", samesite="lax")
    return reponse


_pipeline = PipelineTraduction(taille_modele_whisper="medium")


MODES_VERS_EXTENSION = {
    "doublage": ".mp4",
    "sous_titres": ".mp4",
    "transcription": ".txt",
    "resume": ".txt",
}


def _executer_job_en_arriere_plan(
    job_id: str,
    chemin_video: str,
    youtube_url: str,
    langue_source: str,
    langue_cible: str,
    cloner_voix: bool,
    mode: str,
):
    extension = MODES_VERS_EXTENSION.get(mode, ".mp4")
    chemin_sortie = os.path.join(DOSSIER_OUTPUTS, f"{job_id}{extension}")

    def on_progress(p: ProgressionEtape):
        mettre_a_jour_job(
            job_id,
            statut=StatutJob.EN_COURS,
            etape=p.etape,
            pourcentage_etape=p.pourcentage,
            message=p.message,
        )

    try:
        # Si l'entrée est un lien YouTube plutôt qu'un fichier uploadé,
        # on la télécharge d'abord -- le reste du pipeline ne voit
        # ensuite aucune différence avec un fichier local classique.
        if youtube_url:
            on_progress(ProgressionEtape("extraction", 0, "Téléchargement de la vidéo YouTube..."))
            chemin_video = telecharger_video(youtube_url, DOSSIER_UPLOADS, job_id)
            on_progress(ProgressionEtape("extraction", 100, "Vidéo téléchargée."))

        _pipeline.executer(
            chemin_video=chemin_video,
            langue_source=langue_source,
            langue_cible=langue_cible,
            chemin_sortie=chemin_sortie,
            on_progress=on_progress,
            cloner_voix=cloner_voix,
            mode=mode,
        )
        mettre_a_jour_job(
            job_id,
            statut=StatutJob.TERMINE,
            chemin_video_sortie=chemin_sortie,
            message="Traitement terminé.",
        )
    except ErreurTelechargement as e:
        mettre_a_jour_job(job_id, statut=StatutJob.ERREUR, erreur=str(e))
    except Exception as e:
        mettre_a_jour_job(job_id, statut=StatutJob.ERREUR, erreur=str(e))
    finally:
        if chemin_video and os.path.exists(chemin_video):
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
        "mode": j.mode,
    } for j in lister_jobs()]}


@app.post("/api/traduire")
async def lancer_traduction(
    fichier: UploadFile = File(None),
    youtube_url: str = Form(None),
    langue_source: str = Form(...),
    langue_cible: str = Form(...),
    cloner_voix: bool = Form(False),
    mode: str = Form("doublage"),
):
    if langue_source not in CODES_LANGUES or langue_cible not in CODES_LANGUES:
        raise HTTPException(400, "Langue non supportée.")

    if mode not in MODES_VERS_EXTENSION:
        raise HTTPException(400, f"Mode non supporté : '{mode}'.")

    if not fichier and not youtube_url:
        raise HTTPException(400, "Il faut fournir soit un fichier, soit un lien YouTube.")

    job = creer_job(langue_source=langue_source, langue_cible=langue_cible, mode=mode)
    chemin_video = None

    if fichier:
        chemin_video = os.path.join(DOSSIER_UPLOADS, f"{job.id}_{fichier.filename}")
        with open(chemin_video, "wb") as f:
            while True:
                morceau = await fichier.read(1024 * 1024)
                if not morceau:
                    break
                f.write(morceau)

    thread = threading.Thread(
        target=_executer_job_en_arriere_plan,
        args=(job.id, chemin_video, youtube_url, langue_source, langue_cible, cloner_voix, mode),
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
        raise HTTPException(404, "Résultat non disponible.")

    if job.chemin_video_sortie.endswith(".txt"):
        noms = {"transcription": "transcription", "resume": "resume"}
        nom = noms.get(job.mode, "resultat")
        return FileResponse(
            job.chemin_video_sortie,
            media_type="text/plain",
            filename=f"{nom}_{job_id}.txt",
        )

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