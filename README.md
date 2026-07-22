# VideoDubber

**Doublage automatique de vidéos — 100 % local, libre et gratuit.**

VideoDubber transpose une vidéo dans une autre langue : transcription,
traduction, génération de voix synthétique, et réassemblage. Tout tourne
sur votre machine, sans abonnement, sans API payante, sans envoi de données
à un serveur tiers.

---

## Pipeline

`
Vidéo source
    │
    ▼
┌─ AudioExtractor ────── FFmpeg → WAV 16 kHz mono
│
├─ Transcriber ───────── faster-whisper (medium) → segments + timestamps
│
├─ Translator ────────── Ollama (Qwen 3) / M2M-100 (fallback) → traduction
│
├─ TTS Generator ─────── Kokoro-82M (Apache 2.0) → voix synthétique locale
│
└─ Video Assembler ───── FFmpeg -c:v copy → vidéo finale sans réencodage
`

**Modèles utilisés et leurs licences :**

| Technologie | Rôle | Licence |
|---|---|---|
| faster-whisper | Transcription | MIT |
| Qwen 3 (Ollama) / M2M-100 | Traduction | Apache 2.0 / MIT |
| Kokoro-82M | Synthèse vocale | Apache 2.0 |
| FFmpeg | Extraction / assemblage | LGPL / GPL |
| PyTorch | Moteur de calcul | BSD |

Tous les modèles sous licence **MIT**, **Apache 2.0** ou **BSD** → usage
commercial sans restriction.

---

## Prérequis

- **Docker** et **Docker Compose** (recommandé)
- **Python 3.10+** (si installation sans Docker)
- **FFmpeg** (installé automatiquement dans Docker)
- **8+ Go RAM** recommandé (Kokoro ~3 Go, Whisper ~2 Go, Ollama~6 Go)

---

## Installation & utilisation (Docker — recommandé)

`ash
# 1. Démarrer le stack complet (Ollama + app)
docker compose up -d

# 2. Attendre qu'Ollama ait téléchargé Qwen 3 (~5 min au premier lancement)
docker compose logs -f ollama

# 3. Ouvrir http://localhost:7860
`

Le premier lancement télécharge les modèles (Whisper, Kokoro, Qwen 3).
Comptez 5-15 minutes selon votre connexion.

---

## Installation sans Docker

`ash
# 1. Installer FFmpeg
#    Windows : winget install FFmpeg
#    macOS   : brew install ffmpeg
#    Linux   : sudo apt install ffmpeg

# 2. Installer Ollama (pour la traduction LLM)
#    https://ollama.com/download
#    Puis : ollama pull qwen3:7b

# 3. Installer les dépendances Python
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate      # Windows
pip install -r requirements.txt
`

---

## Utilisation

### Via l'interface web

`ash
cd backend
python -m uvicorn api.main:app --reload
`

Ouvrir **http://127.0.0.1:8000** dans un navigateur.

### Via la ligne de commande

`ash
cd backend
python -m core.pipeline chemin/vers/ma_video.mp4 fr en
`

### API REST

| Endpoint | Méthode | Description |
|---|---|---|
| /api/traduire | POST | Upload vidéo + langues → retourne un job_id |
| /api/statut/{job_id} | GET | Progression en temps réel |
| /api/telecharger/{job_id} | GET | Télécharger la vidéo finale |
| /api/langues | GET | Liste des langues supportées |

---

## Langues supportées

| Code | Langue | Traduction | Voix (Kokoro) |
|---|---|---|---|
| fr | Français | ✅ Qwen 3 / M2M-100 | ✅ ff_siwis |
| en | Anglais | ✅ Qwen 3 / M2M-100 | ✅ am_adam |
| es | Espagnol | ✅ Qwen 3 / M2M-100 | ✅ ef_dora |
| de | Allemand | ✅ Qwen 3 / M2M-100 | ❌ (voix non dispo) |
| it | Italien | ✅ Qwen 3 / M2M-100 | ✅ if_sara |
| pt | Portugais | ✅ Qwen 3 / M2M-100 | ✅ pf_dora |
| ja | Japonais | ✅ Qwen 3 / M2M-100 | ✅ jf_nezumi |
| zh | Chinois | ✅ Qwen 3 / M2M-100 | ✅ zf_xiaobei |
| ko | Coréen | ✅ Qwen 3 / Ollama | ✅ kf_youngmi |
| nl | Néerlandais | ✅ Qwen 3 / Ollama | ❌ (voix non dispo) |
| ar | Arabe | ✅ Qwen 3 / M2M-100 | ❌ (voix non dispo) |
| ru | Russe | ✅ Qwen 3 / M2M-100 | ❌ (voix non dispo) |

- **Traduction** : Qwen 3 (Ollama) pour 100+ langues, M2M-100 (fallback) pour 10.
- **Voix** : Kokoro supporte 8 langues. Les autres langues sont traduites mais
  utilisent la voix anglaise par défaut (am_adam).

---

## Variables d'environnement

| Variable | Défaut | Description |
|---|---|---|
| OLLAMA_URL | http://localhost:11434 | URL du serveur Ollama |
| OLLAMA_MODELE | qwen3:7b | Modèle LLM pour la traduction |
| FORCE_TRADUCTEUR | uto | ollama, m2m, ou uto |

---

## Déploiement (Hugging Face Spaces)

Le projet est compatible Hugging Face Spaces (Docker).

1. Créer un Space Docker sur https://huggingface.co/spaces
2. Pusher le dépôt (ou connecter un repo GitHub)
3. Le start_hf_spaces.sh lance Ollama + FastAPI automatiquement

---

## Architecture du projet

`
VideoDubber/
├── backend/
│   ├── api/
│   │   ├── main.py          # Serveur FastAPI
│   │   └── job_manager.py   # Gestion des jobs
│   └── core/
│       ├── pipeline.py      # Orchestrateur du pipeline
│       ├── audio_extractor.py
│       ├── transcriber.py
│       ├── translator.py    # Ollama + M2M-100 fallback
│       ├── tts_generator.py # Kokoro-82M (Apache 2.0)
│       ├── audio_aligner.py
│       ├── video_assembler.py
│       └── voice_cloner.py  # Optionnel
├── frontend/
│   └── index.html
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
`

---

## Licence

Ce projet est distribué sous licence **MIT**.

Modèles utilisés :
- Kokoro-82M → Apache 2.0
- M2M-100 → MIT
- Qwen 3 → Apache 2.0
- faster-whisper → MIT
- FFmpeg → LGPL/GPL
- PyTorch → BSD
