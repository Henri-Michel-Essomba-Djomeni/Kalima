# API REST — Documentation

L'API est servie par FastAPI sur `http://127.0.0.1:8000`.

Documentation interactive : http://127.0.0.1:8000/docs

## Endpoints

### `GET /api/langues`

Retourne la liste des codes langue supportés.

**Exemple de réponse :**
```json
{
  "langues": ["ar", "de", "en", "es", "fr", "it", "ja", "pt", "ru", "zh"]
}
```

---

### `POST /api/traduire`

Lance le pipeline de traduction sur une vidéo uploadée.

**Paramètres (multipart/form-data) :**
| Champ | Type | Description |
|---|---|---|
| `fichier` | File | Fichier vidéo (MP4, MKV, MOV, WEBM, AVI) |
| `langue_source` | String | Code ISO de la langue source |
| `langue_cible` | String | Code ISO de la langue cible |

**Exemple de réponse :**
```json
{
  "job_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

---

### `GET /api/statut/{job_id}`

Interroge la progression d'un job.

**Exemple de réponse :**
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

**Étapes possibles :** `extraction`, `transcription`, `traduction`,
`voix`, `assemblage`

---

### `GET /api/telecharger/{job_id}`

Télécharge la vidéo finalisée. Disponible uniquement quand le
statut du job est `termine`.

**Réponse :** Fichier MP4 (`video_traduite.mp4`)

**Erreur :** 404 si le job n'existe pas ou n'est pas terminé.

---

## Intégration

Exemple avec `curl` :

```bash
# Lister les langues
curl http://127.0.0.1:8000/api/langues

# Lancer une traduction
curl -X POST http://127.0.0.1:8000/api/traduire \
  -F "fichier=@ma_video.mp4" \
  -F "langue_source=fr" \
  -F "langue_cible=en"

# Vérifier le statut
curl http://127.0.0.1:8000/api/statut/<job_id>

# Télécharger le résultat
curl -o video_finale.mp4 http://127.0.0.1:8000/api/telecharger/<job_id>
```
