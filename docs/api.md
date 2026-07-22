# API REST — Documentation

L'API est servie par FastAPI sur `http://127.0.0.1:8000`.

Documentation interactive : http://127.0.0.1:8000/docs

## Endpoints

### `GET /api/langues`

Retourne la liste des codes langue supportés.

**Exemple de réponse :**
```json
{
  "langues": ["ar", "de", "en", "es", "fr", "it", "ja", "ko", "nl", "pt", "ru", "zh"]
}
```

---

### `GET /api/jobs`

Liste les 20 derniers jobs avec leur statut et progression.

**Exemple de réponse :**
```json
{
  "jobs": [
    {
      "id": "a1b2c3d4-...",
      "statut": "termine",
      "etape": "assemblage",
      "pourcentage_etape": 100.0,
      "message": "Traduction terminee.",
      "langue_source": "fr",
      "langue_cible": "en",
      "cree_le": "2026-07-22T12:00:00"
    }
  ]
}
```

---

### `POST /api/traduire`

Lance le pipeline de traduction sur une video uploadee.

**Parametres (multipart/form-data) :**
| Champ | Type | Description |
|---|---|---|
| `fichier` | File | Fichier video (MP4, MKV, MOV, WEBM, AVI) |
| `langue_source` | String | Code ISO de la langue source |
| `langue_cible` | String | Code ISO de la langue cible |

**Exemple de reponse :**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

### `GET /api/statut/{job_id}`

Interroge la progression d'un job.

**Exemple de reponse :**
```json
{
  "statut": "en_cours",
  "etape": "traduction",
  "pourcentage_etape": 45.0,
  "message": "Segment 5/11 traduit.",
  "erreur": null
}
```

**Statuts possibles :** `en_attente`, `en_cours`, `termine`, `erreur`

---

### `GET /api/telecharger/{job_id}`

Telecharge la video finalisee.

**Reponse :** Fichier MP4 (`video_traduite.mp4`)

---

### `GET /api/sous-titres/{job_id}?format=srt|vtt`

Telecharge les sous-titres de la video traduite.

**Parametres :**
| Champ | Type | Defaut | Description |
|---|---|---|---|
| `format` | String | `srt` | `srt` ou `vtt` |

**Reponse :** Fichier texte (`.srt` ou `.vtt`)

---

### `GET /api/transcription/{job_id}?format=txt|json`

Telecharge la transcription complete (original + traduction).

**Parametres :**
| Champ | Type | Defaut | Description |
|---|---|---|---|
| `format` | String | `txt` | `txt` (texte brut) ou `json` (structure) |

---

### `POST /api/tts`

Synthese vocale depuis un texte (mode voix-off).

**Parametres (multipart/form-data) :**
| Champ | Type | Defaut | Description |
|---|---|---|---|
| `texte` | String | -- | Texte a synthetiser |
| `langue` | String | `fr` | Code ISO de la langue |

**Reponse :** Fichier WAV (`audio.wav`)

---

## Integration

Exemple avec `curl` :

```bash
# Lister les langues
curl http://127.0.0.1:8000/api/langues

# Lancer une traduction
curl -X POST http://127.0.0.1:8000/api/traduire \
  -F "fichier=@ma_video.mp4" \
  -F "langue_source=fr" \
  -F "langue_cible=en"

# Verifier le statut
curl http://127.0.0.1:8000/api/statut/<job_id>

# Telecharger le resultat
curl -o video_finale.mp4 http://127.0.0.1:8000/api/telecharger/<job_id>

# Sous-titres SRT
curl -o sous-titres.srt http://127.0.0.1:8000/api/sous-titres/<job_id>?format=srt

# Transcription texte
curl -o transcription.txt http://127.0.0.1:8000/api/transcription/<job_id>?format=txt

# Synthese vocale (voix-off)
curl -X POST http://127.0.0.1:8000/api/tts \
  -F "texte=Bonjour le monde" \
  -F "langue=fr" \
  -o audio.wav
```
