# VideoDubber — Pipeline core

## Installation

```bash
# FFmpeg (déjà installé chez toi, mais requis)
sudo apt update && sudo apt install ffmpeg -y   # ou winget install FFmpeg sur Windows

# Dépendances Python
pip install -r requirements.txt --break-system-packages   # ou sans ce flag si tu es dans un venv
```

## Tester le pipeline en ligne de commande (avant l'interface)

```bash
cd backend
python -m core.pipeline chemin/vers/ma_video.mp4 fr en
```

Ça va :
1. Extraire l'audio complet (pas de découpage en chunks fixes)
2. Transcrire avec faster-whisper (segmentation automatique par silence)
3. Traduire chaque segment avec NLLB-200
4. Générer une voix anglaise cohérente par segment, calée sur le timing d'origine
5. Produire `video_traduite_finale.mp4` — vidéo copiée telle quelle, seul l'audio change

## Langues disponibles pour l'instant

fr, en, es, de, it, pt, ar, zh, ja, ru
(facile à étendre — voir `CODES_LANGUES_NLLB` dans `translator.py` et `VOIX_PAR_LANGUE` dans `tts_generator.py`)

## Prochaine étape

Construire l'API FastAPI (`backend/api/`) + l'interface web (`frontend/`)
qui appellent `PipelineTraduction` avec suivi de progression en temps réel.

Terminé — voir plus bas.

## Lancer l'application complète (interface web)

```powershell
cd backend
python -m uvicorn api.main:app --reload
```

Puis ouvre **http://127.0.0.1:8000** dans ton navigateur.

Dépose une vidéo, choisis les langues source/cible, lance la traduction —
la progression s'affiche en temps réel étape par étape (extraction,
transcription, traduction, voix, assemblage), et un lien de téléchargement
apparaît une fois la vidéo prête.

Les vidéos uploadées sont automatiquement supprimées après traitement ;
seule la vidéo finale reste dans `outputs/` jusqu'à ce que tu la
télécharges (tu peux la supprimer manuellement ensuite).

## Ce qui a changé par rapport au prototype initial

- Plus de découpage vidéo fixe toutes les 60s → segmentation par silence, phrases jamais coupées
- `faster-whisper` medium au lieu de `whisper-base` → bien plus précis
- `NLLB-200` au lieu d'un modèle par paire de langues → langues changeables facilement
- `edge-tts` au lieu de `gTTS` → voix neuronale cohérente, pas robotique
- Calibrage de la vitesse de la voix pour respecter le timing du segment d'origine
- Vidéo jamais réencodée (`-c:v copy`) → rapide et sans perte, même sur des fichiers lourds
- Bug d'encodage UTF-8/Latin-1 corrigé (fini les "annÃ©es")
