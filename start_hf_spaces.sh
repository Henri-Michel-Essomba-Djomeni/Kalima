#!/bin/bash
# Script d'entrée pour Hugging Face Spaces
# Lance Ollama en arrière-plan puis démarre l'app FastAPI.

set -e

# Démarrer Ollama en arrière-plan
ollama serve &
OLLAMA_PID=$!

# Attendre qu'Ollama soit prêt
echo "Attente d'Ollama..."
until curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 1
done
echo "Ollama prêt."

# Puller le modèle si pas déjà fait
ollama pull qwen3:7b 2>/dev/null || echo "Modèle déjà présent."

# Démarrer FastAPI
uvicorn backend.api.main:app --host 0.0.0.0 --port 7860
