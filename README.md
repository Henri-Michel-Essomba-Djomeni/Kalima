# Kalima

Doublage automatique de vidéos : transcription, traduction, génération de
voix (générique ou clonée à partir de la voix d'origine), export de
sous-titres, et réassemblage final. Traitement 100% local, stack
entièrement libre de droits pour un usage commercial.

**Pipeline :** extraction audio → transcription (faster-whisper) →
traduction (Ollama/Qwen 3, repli automatique sur M2M-100) → génération de
voix (Kokoro-82M, ou clonage OpenVoice en option) → réassemblage vidéo
(FFmpeg, sans réencodage).

---

## 1. Installation de base

```bash
# FFmpeg (système, requis dans tous les cas)
sudo apt update && sudo apt install ffmpeg -y   # ou : winget install FFmpeg (Windows)

# Dépendances Python
pip install -r requirements.txt
```

Ça installe tout ce qu'il faut pour le pipeline de base : transcription,
traduction (M2M-100), voix générique (Kokoro-82M), interface web, export
SRT/VTT, persistance des jobs en SQLite.

**Traduction de meilleure qualité (optionnel)** : installe
[Ollama](https://ollama.com) et lance `ollama pull qwen3:7b` — le
pipeline bascule automatiquement dessus s'il est disponible, sinon
il retombe sur M2M-100 sans rien à configurer.

**Le clonage de voix est optionnel et s'installe à part** (section 4).

## 2. Tester en ligne de commande

```bash
cd backend
python -m core.pipeline chemin/vers/ma_video.mp4 langue_source langue_cible
# Exemple : python -m core.pipeline film.mp4 fr en
# Avec clonage de la voix d'origine : ajoute --cloner-voix
```

## 3. Lancer l'application complète (interface web)

```bash
cd backend
python -m uvicorn api.main:app --reload
```

Puis ouvre **http://127.0.0.1:8000**. Dépose une vidéo, choisis les
langues, coche "Cloner la voix d'origine" si tu veux, lance la
traduction — la progression s'affiche en temps réel étape par étape.
Une fois terminé : téléchargement de la vidéo doublée et des sous-titres.

Protège l'accès avant d'exposer le serveur (tunnel, réseau local, etc.) :
```bash
export KALIMA_USER="ton_nom"
export KALIMA_PASS="un_mot_de_passe_solide"
```
(par défaut : `admin` / `changemoi` — à changer avant toute exposition publique)

## 4. API REST

Voir `docs/api.md` pour le détail complet des endpoints
(`/api/traduire`, `/api/statut`, `/api/telecharger`, `/api/sous-titres`,
`/api/transcription`, `/api/tts`, `/api/jobs`, `/api/langues`,
`/api/langues-clonables`). Documentation interactive sur `/docs`.

**Langues de traduction disponibles :** fr, en, es, de, it, pt, ar, zh,
ja, ru (M2M-100 et Ollama), plus nl, pl, tr, vi, th, hi, ko (Ollama
uniquement — nécessite Ollama installé).

---

## 5. Clonage de la voix d'origine (optionnel)

Par défaut, la voix traduite est générique (Kokoro-82M). Le clonage
vocal fait imiter à la voix traduite le timbre de la personne dans la
vidéo, via [OpenVoice v2](https://github.com/myshell-ai/OpenVoice)
(licence MIT, utilisable commercialement).

**Langues supportées pour le clonage :** anglais, espagnol, français,
chinois, japonais. Pour toute autre langue cible, l'app bascule
automatiquement sur la voix générique Kokoro-82M (rien ne casse).

L'installation est en plusieurs étapes parce qu'OpenVoice/MeloTTS ont
des dépendances anciennes et très nombreuses qui entrent en conflit
avec le reste du projet. Voir le détail complet dans
`docs/voice-cloning.md`. Résumé des commandes :

```bash
pip install --no-deps git+https://github.com/myshell-ai/OpenVoice.git
pip install --no-deps git+https://github.com/myshell-ai/MeloTTS.git
pip install librosa anyascii cached_path cn2an eng_to_ipa fugashi g2p_en g2pkk gradio gruut inflect jamo jieba langid loguru mecab-python3 num2words pykakasi pypinyin tensorboard torchaudio txtsplit unidecode unidic wavmark whisper-timestamped
python -m unidic download
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"

cd backend
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='myshell-ai/OpenVoiceV2', local_dir='checkpoints_v2')"
```

Le clonage est nettement plus lent que la voix générique, surtout sur
CPU. Le terminal affiche clairement ce qui se passe : `[+] Chargement
du convertisseur de timbre OpenVoice...` si le clonage démarre bien, ou
`[!] repli sur la voix générique -- <raison>` en cas de souci sur un
segment (le pipeline ne plante jamais pour autant).

---

## 6. Licences et conformité

Toute la stack par défaut (transcription, traduction, voix, code) est
utilisable commercialement sans restriction. Détail complet dans
`docs/licensing.md`. En bref :

| Composant | Licence |
|---|---|
| faster-whisper | MIT |
| M2M-100 | MIT |
| Qwen 3 (Ollama) | Apache 2.0 |
| Kokoro-82M | Apache 2.0 |
| OpenVoice v2 / MeloTTS (clonage, optionnel) | MIT |
| Code du projet | MIT |

⚠️ **Avant toute commercialisation**, voir aussi `COMMERCIALISATION.md`
pour l'analyse légale complète (droits sur le contenu traduit, EU AI
Act, consentement pour le clonage vocal) — la conformité des licences
techniques ne suffit pas à elle seule à sécuriser un usage commercial.

## 7. Autres documents

- `docs/architecture.md` — vue d'ensemble technique du pipeline
- `docs/api.md` — référence complète de l'API REST
- `docs/voice-cloning.md` — installation détaillée du clonage vocal
- `docs/licensing.md` — détail des licences de chaque dépendance
- `FONCTIONNALITES.md` — état des lieux des fonctionnalités
- `COMMERCIALISATION.md` — analyse marché/légale/technique
- `CONTRIBUTING.md` — comment contribuer au projet
