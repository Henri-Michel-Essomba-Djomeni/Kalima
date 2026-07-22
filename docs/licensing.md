# Licences et conformité légale

Ce document détaille les licences de chaque composant utilisé par
VideoDubber, pour garantir une utilisation commerciale sans risque.

## Code du projet — MIT

Le code source de VideoDubber est distribué sous licence MIT.
Vous pouvez l'utiliser, le modifier, le distribuer et le vendre
sans restriction, à condition de conserver l'avis de copyright.

## Dépendances Python et leurs licences

| Bibliothèque | Licence | Usage commercial |
|---|---|---|
| faster-whisper | MIT | ✅ Libre |
| transformers (HuggingFace) | Apache 2.0 | ✅ Libre |
| PyTorch | BSD | ✅ Libre |
| Kokoro-82M | Apache 2.0 | ✅ Libre |
| Ollama (client Python) | MIT | ✅ Libre |
| sentencepiece | Apache 2.0 | ✅ Libre |
| pydub | MIT | ✅ Libre |
| requests | Apache 2.0 | ✅ Libre |
| fastapi | MIT | ✅ Libre |
| uvicorn | BSD | ✅ Libre |
| python-multipart | Apache 2.0 | ✅ Libre |

## Modèles de machine learning

| Modèle | Licence | Usage commercial |
|---|---|---|
| **faster-whisper** (poids) | MIT | ✅ Libre |
| **M2M-100** (facebook/m2m100_418M) | MIT | ✅ Libre |
| **Kokoro-82M** (poids + code) | Apache 2.0 | ✅ Libre |
| **Qwen 3** (via Ollama) | Apache 2.0 | ✅ Libre |
| OpenVoice v2 (optionnel) | MIT | ✅ Libre |

## Pourquoi Kokoro-82M plutôt que Piper TTS ?

Piper TTS (MIT) a été **archivé** par son créateur en octobre 2025.
Le seul fork maintenu est passé en **GPL-3.0**, ce qui pose des
problèmes de copyleft pour un produit commercial closed-source.

Kokoro-82M (Apache 2.0) le remplace avec :
- Licence Apache 2.0 — plus permissive que MIT
- Qualité vocale quasi-humaine (score MOS 4.2/5)
- 82M paramètres, fonctionne sur CPU (~3 Go RAM)
- 54 voix pré-définies dans 8 langues

## Pourquoi Qwen 3 (Ollama) plutôt que M2M-100 ?

M2M-100 (MIT) est conservé comme fallback, mais Qwen 3 (Apache 2.0)
via Ollama offre une qualité de traduction bien supérieure :
- Compréhension contextuelle (LLM vs NMT)
- 100+ langues supportées
- ~76% MMLU vs ~36 BLEU pour M2M-100
- Fonctionne localement, sans cloud

## FFmpeg

FFmpeg est utilisé comme sous-processus (pas de liaison directe).
Il est sous licence LGPL/GPL. Son utilisation comme outil système
n'affecte pas la licence de VideoDubber.

## Clonage vocal

Le module optionnel de clonage vocal (OpenVoice v2) est sous licence
MIT, compatible avec un usage commercial.

## UE AI Act

Depuis août 2026, le règlement européen sur l'IA exige que les
contenus générés ou modifiés par IA soient identifiés comme tels.
