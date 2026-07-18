# VideoDubber

Doublage automatique de vidéos : transcription, traduction, génération de
voix (générique ou clonée à partir de la voix d'origine), et réassemblage
final. Traitement 100% local, interface web incluse.

**Pipeline :** extraction audio → transcription (Whisper) → traduction
(NLLB-200) → génération de voix (edge-tts ou clonage OpenVoice) →
réassemblage vidéo (FFmpeg, sans réencodage).

---

## 1. Installation de base

```bash
# FFmpeg (système, requis dans tous les cas)
sudo apt update && sudo apt install ffmpeg -y   # ou : winget install FFmpeg (Windows)

# Dépendances Python
pip install -r requirements.txt
```

Ça installe tout ce qu'il faut pour le pipeline de base : transcription,
traduction, voix générique (edge-tts), interface web. **Le clonage de
voix est optionnel et s'installe à part** (section 4).

## 2. Tester le pipeline en ligne de commande

```bash
cd backend
python -m core.pipeline chemin/vers/ma_video.mp4 langue_source langue_cible
# Exemple : python -m core.pipeline film.mp4 fr en
```

Produit `video_traduite_finale.mp4` dans le dossier courant.

## 3. Lancer l'application complète (interface web)

```powershell
cd backend
python -m uvicorn api.main:app --reload
```

Puis ouvre **http://127.0.0.1:8000**. Dépose une vidéo, choisis les
langues, lance la traduction — la progression s'affiche en temps réel
étape par étape, et un lien de téléchargement apparaît une fois prêt.

Les vidéos uploadées sont supprimées automatiquement après traitement ;
la vidéo finale reste dans `outputs/` jusqu'au téléchargement.

**Langues disponibles (traduction) :** fr, en, es, de, it, pt, ar, zh, ja, ru
(voir `CODES_LANGUES_NLLB` dans `backend/core/translator.py` pour en ajouter)

---

## 4. Clonage de la voix d'origine (optionnel)

Par défaut, la voix traduite est générique (edge-tts). Le clonage vocal
fait imiter à la voix traduite le timbre de la personne dans la vidéo,
via [OpenVoice v2](https://github.com/myshell-ai/OpenVoice) (licence MIT,
utilisable commercialement — contrairement à XTTS-v2 dont la licence
interdit l'usage commercial).

**Langues supportées pour le clonage :** anglais, espagnol, français,
chinois, japonais. Pour toute autre langue cible, l'app bascule
automatiquement sur la voix générique edge-tts (rien ne casse).

L'installation est en plusieurs étapes parce qu'OpenVoice/MeloTTS ont
des dépendances anciennes et très nombreuses qui entrent en conflit
avec le reste du projet. Voici la procédure complète, testée de bout
en bout :

### 4.1 — Installer OpenVoice et MeloTTS sans leurs dépendances automatiques

```bash
pip install --no-deps git+https://github.com/myshell-ai/OpenVoice.git
pip install --no-deps git+https://github.com/myshell-ai/MeloTTS.git
```

`--no-deps` est nécessaire : OpenVoice exige une version figée très
ancienne de `faster-whisper` (0.9.0) qui entrerait en conflit avec la
version récente utilisée pour la transcription principale. On installe
donc leurs propres dépendances manuellement à l'étape suivante.

### 4.2 — Installer les sous-dépendances manquantes

```bash
pip install librosa anyascii cached_path cn2an eng_to_ipa fugashi g2p_en g2pkk gradio gruut inflect jamo jieba langid loguru mecab-python3 num2words pykakasi pypinyin tensorboard torchaudio txtsplit unidecode unidic wavmark whisper-timestamped
```

**Ignore les avertissements** du type `melotts requires librosa==0.9.1,
but you have librosa 0.11.0` — ce sont des versions figées trop
strictes déclarées par OpenVoice/MeloTTS, pas de vraies erreurs. Ne
réinstalle surtout pas les versions plus anciennes qu'ils réclament
(ça casserait le reste du pipeline qui fonctionne déjà avec des
versions plus récentes).

### 4.3 — Télécharger le dictionnaire unidic (japonais, requis même sans l'utiliser)

MeloTTS importe son module de support japonais au chargement, même si
tu ne comptes t'en servir que pour l'anglais ou le français. Sans ce
dictionnaire, l'import plante.

```bash
python -m unidic download
```

(~500 Mo, peut prendre plusieurs minutes)

### 4.4 — Télécharger une ressource NLTK manquante

```bash
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"
```

### 4.5 — Vérifier que tout s'importe correctement

```bash
python -c "from melo.api import TTS"
```

Si cette commande ne renvoie **aucune erreur** (des téléchargements de
modèles au premier lancement sont normaux), l'installation est bonne.
Si elle plante encore, l'erreur affichée nomme presque toujours le
module manquant précis — l'installer avec `pip install <nom>` et
réessayer.

### 4.6 — Télécharger les checkpoints OpenVoice v2

Le lien S3 officiel d'OpenVoice est instable pour beaucoup d'utilisateurs
(erreurs 404/accès refusé). Le plus fiable est de passer par Hugging Face,
via `huggingface_hub` (déjà installé avec les dépendances de base) :

```bash
cd backend
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='myshell-ai/OpenVoiceV2', local_dir='checkpoints_v2')"
```

Vérifie la structure obtenue (elle doit ressembler à ça) :
```
backend/checkpoints_v2/
  converter/
    config.json
    checkpoint.pth
  base_speakers/
    ses/
      en-us.pth, fr.pth, es.pth, zh.pth, jp.pth, ...
```

### 4.7 — Utilisation

- **En CLI** : ajoute `--cloner-voix` à la commande
  ```bash
  python -m core.pipeline ma_video.mp4 fr en --cloner-voix
  ```
- **Dans l'interface web** : coche la case "Cloner la voix d'origine"
  (grisée automatiquement si la langue cible choisie n'est pas clonable).

Le clonage est nettement plus lent que la voix générique, surtout sur
CPU (chargement de MeloTTS + OpenVoice, extraction de l'empreinte
vocale, conversion de timbre par segment) — prévois plus de temps de
traitement qu'avec la voix générique.

Le terminal affiche clairement ce qui se passe : `[+] Chargement du
convertisseur de timbre OpenVoice...` et `[+] Modèle MeloTTS chargé...`
si le clonage démarre bien, ou `[!] repli sur la voix générique --
<raison>` s'il y a un souci sur un segment (le pipeline ne plante
jamais pour autant, il continue avec la voix générique sur ce segment).

---

## Ce qui a changé par rapport au prototype initial

- Plus de découpage vidéo fixe toutes les 60s → segmentation par silence, phrases jamais coupées
- `faster-whisper` medium au lieu de `whisper-base` → bien plus précis
- `NLLB-200` au lieu d'un modèle par paire de langues → langues changeables facilement
- `edge-tts` au lieu de `gTTS` → voix neuronale cohérente, pas robotique
- Calibrage de la vitesse de la voix pour respecter le timing du segment d'origine
- Vidéo jamais réencodée (`-c:v copy`) → rapide et sans perte, même sur des fichiers lourds
- Bug d'encodage UTF-8/Latin-1 corrigé (fini les "annÃ©es")
- Clonage de la voix d'origine (optionnel, voir section 4)