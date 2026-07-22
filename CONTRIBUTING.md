# Contribuer à VideoDubber

## Principes

1. **Licences** : tout ajout de dépendance doit utiliser une licence
   compatible MIT (pas de CC BY-NC, pas de CPML).
2. **Local** : privilégier les solutions 100 % locales. Aucun appel
   à une API externe sans justification solide.
3. **Performances** : le pipeline doit pouvoir tourner sur un CPU
   grand public (8 Go RAM recommandés).

## Branches

| Branche | Description |
|---|---|
| `main` | Version originale (NLLB-200 + edge-tts) |
| `clean/legal-free` | Version juridiquement propre (M2M-100 + Piper TTS) |

Toute contribution doit cibler la branche appropriée.

## Conventions de code

- Python 3.10+ (type hints obligatoires)
- Pas de commentaires dans le code (sauf docstrings)
- Docstrings en français pour les modules publics
- Noms de variables en français (cohérence avec le code existant)
- Une classe par fichier, un fichier par module

## Tests

```bash
# À la racine du projet
python -m pytest tests/
```

Avant de soumettre une PR, vérifiez que :
- `pip install -r requirements.txt` fonctionne
- `python -m core.pipeline` affiche l'aide
- `python -m uvicorn api.main:app` démarre sans erreur

## Guide pour l'ajout d'une langue

1. Ajouter le code langue dans `CODES_LANGUES_M2M` (`translator.py`)
2. Ajouter une voix Piper correspondante dans `VOIX_PAR_LANGUE`
   (`tts_generator.py`)
3. Ajouter le nom affiché dans `NOMS_LANGUES` (`frontend/index.html`)
