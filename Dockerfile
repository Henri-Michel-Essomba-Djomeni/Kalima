FROM python:3.12-slim

WORKDIR /app

# FFmpeg (extraction audio + assemblage vidéo)
RUN apt-get update && apt-get install -y ffmpeg && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer kokoro complet (54 voix, 9 langues) au lieu de kokoro-onnx
RUN pip install --no-cache-dir kokoro>=0.7

COPY . .

ENV OLLAMA_URL=http://ollama:11434
ENV OLLAMA_MODELE=qwen3:7b

EXPOSE 7860

CMD ["uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "7860"]
