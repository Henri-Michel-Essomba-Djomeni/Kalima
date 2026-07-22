import os
import wave
import numpy as np
from pathlib import Path
from typing import Optional

class ErreurTTS(Exception):
    pass

_BACKEND = None

VOIX_KOKORO = {}
LANGUES_SUPPORTEES = []

try:
    from kokoro import KPipeline

    VOIX_KOKORO = {
        "fr": {"lang": "f", "voix": "ff_siwis"},
        "en": {"lang": "a", "voix": "am_adam"},
        "es": {"lang": "e", "voix": "ef_dora"},
        "it": {"lang": "i", "voix": "if_sara"},
        "pt": {"lang": "p", "voix": "pf_dora"},
        "ja": {"lang": "j", "voix": "jf_nezumi"},
        "zh": {"lang": "z", "voix": "zf_xiaobei"},
        "ko": {"lang": "k", "voix": "kf_youngmi"},
        "hi": {"lang": "h", "voix": "hf_alpha"},
    }
    LANGUES_SUPPORTEES = list(VOIX_KOKORO.keys())
    _BACKEND = "kokoro"

except ImportError:
    try:
        from kokoro_onnx import Kokoro

        _CHEMIN_BASE = Path(__file__).resolve().parent.parent.parent
        _EMPLACEMENTS_MODELE = [
            _CHEMIN_BASE / "models",
            _CHEMIN_BASE / "backend" / "core" / "models",
            Path.cwd() / "models",
            Path(os.environ.get("KOKORO_MODELS_DIR", "")) if os.environ.get("KOKORO_MODELS_DIR") else None,
        ]
        _EMPLACEMENTS_MODELE = [p for p in _EMPLACEMENTS_MODELE if p]

        _CHEMIN_MODELE = None
        _CHEMIN_VOIX = None
        for d in _EMPLACEMENTS_MODELE:
            model = d / "kokoro-v1.0.onnx"
            voix = d / "voices-v1.0.bin"
            if model.exists() and voix.exists():
                _CHEMIN_MODELE = str(model)
                _CHEMIN_VOIX = str(voix)
                break

        if not _CHEMIN_MODELE:
            _CHEMIN_MODELE = str(_CHEMIN_BASE / "models" / "kokoro-v1.0.onnx")
            _CHEMIN_VOIX = str(_CHEMIN_BASE / "models" / "voices-v1.0.bin")

        VOIX_KOKORO = {
            "en": {"voix": "am_adam", "lang_bcp47": "en-us"},
            "en-gb": {"voix": "bm_george", "lang_bcp47": "en-gb"},
        }
        LANGUES_SUPPORTEES = list(VOIX_KOKORO.keys())
        _BACKEND = "kokoro-onnx"

    except ImportError:
        _BACKEND = None


class GenerateurVoix:
    def __init__(self):
        self._instance = None
        self._pipelines: dict[str, object] = {}

    def generer(self, texte: str, langue: str, chemin_sortie: str, vitesse: float = 1.0) -> str:
        if not texte.strip():
            raise ErreurTTS("Texte vide, rien à synthétiser.")

        info = VOIX_KOKORO.get(langue) or VOIX_KOKORO.get("en")
        if info is None:
            raise ErreurTTS(f"Langue '{langue}' non supportée. Supportées : {LANGUES_SUPPORTEES}")

        if _BACKEND == "kokoro":
            morceaux = []
            pipeline = self._pipeline_kokoro(langue, info["lang"])
            for audio, _ in pipeline(texte, voice=info["voix"], speed=vitesse):
                morceaux.append(audio)
            if not morceaux:
                raise ErreurTTS("Aucun audio généré.")
            audio_complet = np.concatenate(morceaux)
            sample_rate = 24000

        elif _BACKEND == "kokoro-onnx":
            instance = self._instance_onnx()
            lang_bcp47 = info.get("lang_bcp47", "en-us")
            audio_complet, sample_rate = instance.create(
                texte, voice=info["voix"], speed=vitesse, lang=lang_bcp47
            )

        else:
            raise ErreurTTS("Aucun backend TTS disponible. Installez kokoro ou kokoro-onnx.")

        os.makedirs(os.path.dirname(chemin_sortie) or ".", exist_ok=True)
        with wave.open(chemin_sortie, "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes((audio_complet * 32767).astype(np.int16).tobytes())

        return chemin_sortie

    def _pipeline_kokoro(self, langue: str, lang_code: str):
        if langue not in self._pipelines:
            from kokoro import KPipeline
            self._pipelines[langue] = KPipeline(lang_code=lang_code)
        return self._pipelines[langue]

    def _instance_onnx(self):
        if self._instance is None:
            from kokoro_onnx import Kokoro
            if not os.path.exists(_CHEMIN_MODELE) or not os.path.exists(_CHEMIN_VOIX):
                raise ErreurTTS(
                    f"Modèles kokoro-onnx introuvables. "
                    f"Téléchargez-les depuis https://github.com/thewh1teagle/kokoro-onnx/releases:\n"
                    f"  wget -P models/ {_URL_MODELE}\n"
                    f"  wget -P models/ {_URL_VOIX}"
                )
            self._instance = Kokoro(str(_CHEMIN_MODELE), str(_CHEMIN_VOIX))
        return self._instance


_URL_MODELE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
_URL_VOIX = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

_GENERATEUR_VOIX: Optional[GenerateurVoix] = None


def generer_voix(
    texte: str,
    langue: str,
    chemin_sortie: str,
    taux_vitesse: str = "+0%",
) -> str:
    global _GENERATEUR_VOIX
    if _GENERATEUR_VOIX is None:
        _GENERATEUR_VOIX = GenerateurVoix()

    pourcentage = int(taux_vitesse.replace("+", "").replace("%", ""))
    vitesse = 1.0 + pourcentage / 100.0

    return _GENERATEUR_VOIX.generer(texte, langue, chemin_sortie, vitesse=vitesse)


if __name__ == "__main__":
    print(f"Backend TTS : {_BACKEND}")
    print(f"Langues supportées : {LANGUES_SUPPORTEES}")

    if _BACKEND == "kokoro":
        generer_voix(
            "This is a test of Kokoro TTS running locally.",
            langue="en",
            chemin_sortie="test_kokoro.wav",
        )
        print("Fichier test_kokoro.wav généré.")
    elif _BACKEND == "kokoro-onnx":
        if os.path.exists(_CHEMIN_MODELE) and os.path.exists(_CHEMIN_VOIX):
            generer_voix(
                "This is a test of Kokoro ONNX TTS.",
                langue="en",
                chemin_sortie="test_kokoro_onnx.wav",
            )
            print("Fichier test_kokoro_onnx.wav généré.")
        else:
            print(f"Modèles non trouvés. Téléchargez-les :\n  wget -P models/ {_URL_MODELE}\n  wget -P models/ {_URL_VOIX}")
