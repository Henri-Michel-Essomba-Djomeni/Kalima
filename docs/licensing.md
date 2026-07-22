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
| **Piper TTS** (voix) | MIT | ✅ Libre |
| OpenVoice v2 (optionnel) | MIT | ✅ Libre |
| MeloTTS (optionnel) | MIT | ✅ Libre |

## Pourquoi M2M-100 plutôt que NLLB-200 ?

Le modèle NLLB-200 de Meta est distribué sous licence
**CC BY-NC 4.0** (Creative Commons Attribution-NonCommercial).
Cette licence **interdit l'usage commercial**. M2M-100, également
de Meta, est sous licence **MIT** — usage commercial sans restriction.

C'est le changement principal de la branche `clean/legal-free`.

## Pourquoi Piper TTS plutôt que edge-tts ?

Le package `edge-tts` (GPL v3) détourne l'API Bing Speech de
Microsoft pour fournir un service TTS gratuit. Bien que pratique
en usage personnel, cette approche présente deux risques en
environnement commercial :

1. **Légal** : utilisation non autorisée d'une API Microsoft sans
   abonnement Azure
2. **Technique** : l'API peut être modifiée ou coupée à tout moment
   sans préavis

Piper TTS est un système 100 % local, sous licence MIT, qui ne
dépend d'aucun service externe.

## FFmpeg

FFmpeg est utilisé comme sous-processus (pas de liaison directe).
Il est sous licence LGPL/GPL. Son utilisation comme outil système
n'affecte pas la licence de VideoDubber.

## Clonage vocal

Le module optionnel de clonage vocal (OpenVoice v2 + MeloTTS)
est sous licence MIT, compatible avec un usage commercial. Notez
que le clonage de la voix d'une personne sans son consentement
explicite peut violer les lois sur le droit à l'image selon
les juridictions.

## UE AI Act

Depuis août 2026, le règlement européen sur l'IA exige que les
contenus générés ou modifiés par IA soient identifiés comme tels.
Prévoyez d'ajouter un label ou un watermark sur les vidéos
produites si vous distribuez l'application dans l'UE.
