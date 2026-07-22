# VideoDubber — Évaluation fonctionnelle

## Fonctionnalités opérationnelles

| Module | Technologie | Licence | Statut |
|---|---|---|---|
| Upload vidéo via interface web | FastAPI + dropzone | — | OK |
| Extraction audio | FFmpeg (pcm_s16le, 16kHz mono) | LGPL/GPL | OK |
| Transcription | faster-whisper (medium, VAD) | MIT | OK |
| Traduction | M2M-100 (418M) | MIT | OK |
| Synthèse vocale | Piper TTS | MIT | OK |
| Calibrage temporel | Ajustement vitesse par segment | — | OK |
| Assemblage vidéo | FFmpeg -c:v copy (sans réencodage) | LGPL/GPL | OK |
| Progression temps réel | Pooling HTTP vers frontend | — | OK |
| API REST | 4 endpoints (traduire, statut, telecharger, langues) | — | OK |
| CLI | `python -m core.pipeline video.mp4 source target` | — | OK |
| Clonage vocal optionnel | OpenVoice v2 + MeloTTS (en, es, fr, zh, ja) | MIT | Optionnel |

**Pile technique :** Whisper → M2M-100 → Piper TTS → FFmpeg  
**100 % local et libre** : aucun appel réseau, toutes les licences sont MIT/BSD.

## Fonctionnalités absentes — propositions

- **Génération voix off pour texte / PDF** — Aucun endpoint dédié. Pourtant
  `core/tts_generator.py` peut être réutilisé directement : parser le fichier
  texte ou PDF (via PyMuPDF), découper en segments, générer l'audio avec
  Piper TTS, assembler un fichier MP3 final.

- **Export sous-titres (SRT / VTT)** — La transcription et la traduction
  produisent déjà des segments avec timestamps exacts. Il manque juste un
  endpoint qui sérialise ces segments au format SRT ou VTT.

- **Téléchargement transcription seule** — Les textes transcrits et traduits
  sont disponibles en interne mais aucun endpoint ne les expose au
  téléchargement (txt, json, srt).

- **Édition des sous-titres avant synthèse** — Pas d'interface pour
  relire/corriger la transcription ou la traduction avant de lancer la
  génération voix. Utile pour la qualité finale.

- **Traitement batch** — Un seul job à la fois par instance. Pas de file
  d'attente persistante.

- **Persistance des jobs** — Stockage en mémoire (perdu au redémarrage).
  Pour de la production : remplacer par Redis ou une base de données.

- **Support de langues étendu** — 10 langues configurées, mais M2M-100 en
  supporte 100. Il suffit d'ajouter des entrées dans `CODES_LANGUES_M2M`
  et `VOIX_PAR_LANGUE`.

- **Authentification** — Aucune. L'API est ouverte. À sécuriser si
  exposition publique.
