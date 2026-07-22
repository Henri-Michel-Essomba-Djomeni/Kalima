# Clonage vocal — OpenVoice v2

Le clonage vocal est une fonctionnalité **optionnelle**. Par défaut,
VideoDubber utilise Piper TTS (voix générique). Le clonage permet
d'appliquer le timbre de la voix d'origine à la traduction.

## Composants

- **OpenVoice v2** (MyShell AI) — convertisseur de timbre, licence MIT
- **MeloTTS** — synthèse de base, licence MIT

## Installation

```bash
pip install --no-deps git+https://github.com/myshell-ai/OpenVoice.git
pip install --no-deps git+https://github.com/myshell-ai/MeloTTS.git
pip install librosa anyascii cached_path cn2an eng_to_ipa fugashi g2p_en g2pkk gradio gruut inflect jamo jieba langid loguru mecab-python3 num2words pykakasi pypinyin tensorboard torchaudio txtsplit unidecode unidic wavmark whisper-timestamped
python -m unidic download
python -c "import nltk; nltk.download('averaged_perceptron_tagger_eng')"
```

## Téléchargement des checkpoints

```bash
cd backend
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='myshell-ai/OpenVoiceV2', local_dir='checkpoints_v2')"
```

## Langues supportées

| Langue | Code |
|---|---|
| Anglais | en |
| Espagnol | es |
| Français | fr |
| Chinois | zh |
| Japonais | ja |

Pour toute autre langue cible, le pipeline bascule automatiquement
sur la voix générique Piper TTS.

## Utilisation

- **CLI** : ajoutez `--cloner-voix` à la commande
- **Interface web** : cochez la case "Cloner la voix d'origine" (si
  la langue cible est clonable)

## Licence

OpenVoice v2 et MeloTTS sont sous licence MIT — usage commercial libre.
