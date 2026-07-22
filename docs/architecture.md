# Architecture technique

## Vue d'ensemble

VideoDubber est organisé en un pipeline séquentiel à 5 étapes. Chaque
étape est un module indépendant, interchangeable et testable.

```
┌──────────────────────────────────────────────────────────────┐
│                      PipelineTraduction                       │
│                                                              │
│  1. AudioExtractor                                            │
│     └─ extraire_audio(video) → audio.wav                     │
│                                                              │
│  2. Transcripteur                                             │
│     └─ transcrire(audio.wav) → [Segment]                     │
│                                                              │
│  3. Traducteur                                                │
│     └─ traduire_texte(texte, src, tgt) → texte              │
│                                                              │
│  4. AudioAligner                                              │
│     ├─ generer_segment_calibre() → audio segment             │
│     └─ construire_piste_audio_complete() → mix final         │
│                                                              │
│  5. VideoAssembler                                            │
│     └─ assembler_video_finale(video, audio) → output.mp4    │
└──────────────────────────────────────────────────────────────┘
```

## Flux de données

1. **Entrée** : fichier vidéo (MP4, MKV, MOV, WEBM, AVI)
2. **Audio** : extrait en WAV 16 kHz mono via FFmpeg
3. **Segmentation** : faster-whisper découpe la parole en segments
   avec timestamps, via son VAD intégré
4. **Traduction** : chaque segment est traduit via M2M-100
5. **Synthèse** : chaque segment traduit est converti en audio
   via Piper TTS, avec calibrage temporel
6. **Mixage** : tous les segments audio sont placés à leurs
   timestamps sur une piste silencieuse de la durée de la vidéo
7. **Assemblage** : FFmpeg copie le flux vidéo original et
   remplace la piste audio par la nouvelle piste traduite

## Contrôle de progression

`PipelineTraduction` accepte un callback `on_progress` qui reçoit
des objets `ProgressionEtape` contenant :
- `etape` : nom de l'étape en cours
- `pourcentage` : avancement dans l'étape (0-100)
- `message` : texte descriptif

Le callback est appelé après chaque segment traduit et chaque
segment vocal généré, permettant un affichage temps réel.

## Gestion des erreurs

Chaque module expose ses propres exceptions (ex: `ErreurTTS`,
`ErreurTraduction`). Le pipeline les capture et les transmet via
le callback de progression. En cas d'erreur sur un segment
individuel (génération voix), le segment est ignoré et le
pipeline continue.

## Modèles et mémoire

Les modèles Whisper et M2M-100 sont chargés une seule fois dans
l'instance `PipelineTraduction` et réutilisés pour tous les jobs.
Piper TTS charge les modèles vocaux à la demande (un par langue).
