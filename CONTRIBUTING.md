# Contribuer à VideoDubber

## Principes

1. **Licences** : tout ajout de dépendance doit utiliser une licence
   compatible MIT/Apache 2.0 (pas de CC BY-NC, pas de CPML).
2. **Local** : privilégier les solutions 100 % locales. Aucun appel
   à une API externe sans justification solide.
3. **Performances** : le pipeline doit pouvoir tourner sur un CPU
   grand public (8 Go RAM recommandés).

## Branches

| Branche | Description | Stack |
|---|---|---|
| main | Version originale | NLLB-200 + edge-tts |
| clean/legal-free | Version juridiquement propre | Ollama (Qwen 3) + Kokoro-82M |

Toute contribution doit cibler la branche appropriée.

## Conventions de code

- Python 3.10+ (type hints obligatoires)
- Pas de commentaires dans le code (sauf docstrings)
- Docstrings en français pour les modules publics
- Noms de variables en français (cohérence avec le code existant)

## Tests

`ash
python -m pytest tests/
`

Avant de soumettre une PR, vérifiez que :
- pip install -r requirements.txt fonctionne
- python -m core.pipeline affiche l'aide
- python -m uvicorn api.main:app démarre sans erreur

## Guide pour l'ajout d'une langue

1. Ajouter le code langue dans CODES_LANGUES_OLLAMA ou CODES_LANGUES_M2M
   (	ranslator.py)
2. Ajouter une voix Kokoro correspondante dans VOIX_KOKORO
   (	ts_generator.py)
3. Ajouter le nom affiché dans le sélecteur de langue (rontend/index.html)
