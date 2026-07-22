# VideoDubber

**Doublage automatique de vidéos — 100 % local, libre et gratuit.**

VideoDubber transpose une vidéo dans une autre langue : transcription,
traduction, génération de voix synthétique, et réassemblage. Tout tourne
sur votre machine, sans abonnement, sans API payante, sans envoi de données
à un serveur tiers.

---

## Pipeline

```
Vidéo source
    │
    ▼
┌─ AudioExtractor ────── FFmpeg → WAV 16 kHz mono
│
├─ Transcriber ───────── faster-whisper (medium) → segments + timestamps
│
├─ Translator ────────── M2M-100 (Meta, licence MIT) → traduction multilingue
│
├─ TTS Generator ─────── Piper TTS (licence MIT) → voix synthétique locale
│
└─ Video Assembler ───── FFmpeg -c:v copy → vidéo finale sans réencodage
```

**Modèles utilisés et leurs licences :**

| Technologie | Rôle | Licence |
|---|---|---|
| faster-whisper | Transcription | MIT |
| M2M-100 (facebook/m2m100_418M) | Traduction | MIT |
| Piper TTS | Synthèse vocale | MIT |
| FFmpeg | Extraction / assemblage | LGPL / GPL |
| PyTorch | Moteur de calcul | BSD |

Tous les modèles sous licence **MIT** ou **BSD** → usage commercial sans
restriction.

---

## Prérequis

- **Python 3.10+**
- **FFmpeg** installé sur le système
  - Windows : `winget install FFmpeg`
  - macOS : `brew install ffmpeg`
  - Linux : `sudo apt install ffmpeg`
- **Piper TTS** (binaire en ligne de commande)
  - Téléchargement : https://github.com/rhasspy/piper/releases
  - Placer le binaire dans le PATH ou dans un dossier `piper/` à la racine du projet

---

## Installation

```bash
# 1. Cloner le dépôt
git clone https://github.com/Henri-Michel-Essomba-Djomeni/VideoDubber.git
cd VideoDubber

# 2. Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate    # Linux / macOS
venv\Scripts\activate        # Windows

# 3. Installer les dépendances Python
pip install -r requirements.txt
```

---

## Utilisation

### Via l'interface web

```bash
cd backend
python -m uvicorn api.main:app --reload
```

Ouvrir **http://127.0.0.1:8000** dans un navigateur.

Déposer une vidéo, choisir la langue source et la langue cible, lancer la
traduction. La progression s'affiche étape par étape.

### Via la ligne de commande

```bash
cd backend
python -m core.pipeline chemin/vers/ma_video.mp4 fr en
```

Produit `video_traduite_finale.mp4` dans le dossier courant.

### API REST

| Endpoint | Méthode | Description |
|---|---|---|
| `/api/traduire` | POST | Upload vidéo + langues → retourne un job_id |
| `/api/statut/{job_id}` | GET | Progression en temps réel |
| `/api/telecharger/{job_id}` | GET | Télécharger la vidéo finale |
| `/api/langues` | GET | Liste des langues supportées |

---

## Langues supportées

| Code | Langue |
|---|---|
| fr | Français |
| en | Anglais |
| es | Espagnol |
| de | Allemand |
| it | Italien |
| pt | Portugais |
| ru | Russe |
| zh | Chinois (mandarin) |
| ar | Arabe |
| ja | Japonais |

La liste peut être étendue dans `CODES_LANGUES_M2M` (`translator.py`)
et `VOIX_PAR_LANGUE` (`tts_generator.py`).

---

## Clonage vocal (optionnel)

Voir [docs/voice-cloning.md](docs/voice-cloning.md).

Le clonage de voix (OpenVoice v2, licence MIT) est optionnel et nécessite
une installation séparée.

---

## Architecture du projet

```
VideoDubber/
├── backend/
│   ├── api/
│   │   ├── main.py          # Serveur FastAPI
│   │   └── job_manager.py   # Gestion des jobs en mémoire
│   └── core/
│       ├── pipeline.py      # Orchestrateur du pipeline
│       ├── audio_extractor.py  # Extraction audio (FFmpeg)
│       ├── transcriber.py   # Transcription (faster-whisper)
│       ├── translator.py    # Traduction (M2M-100)
│       ├── tts_generator.py # Synthèse vocale (Piper TTS)
│       ├── audio_aligner.py # Calibrage temporel des segments
│       ├── video_assembler.py # Assemblage final (FFmpeg)
│       └── voice_cloner.py  # Clonage vocal optionnel (OpenVoice)
├── frontend/
│   └── index.html           # Interface utilisateur
├── uploads/                 # Vidéos uploadées (temporaire)
├── outputs/                 # Vidéos finalisées
├── voices/                  # Modèles vocaux Piper (téléchargés)
├── requirements.txt
└── README.md
```

---

## Licence

Ce projet est distribué sous licence **MIT**.

Les modèles utilisés sont sous licence MIT ou BSD — aucun verrou légal pour
l'usage commercial.

---

## Branches

| Branche | Description |
|---|---|
| `main` | Version originale (NLLB-200 + edge-tts) |
| `clean/legal-free` | Version juridiquement propre (M2M-100 + Piper TTS) |
