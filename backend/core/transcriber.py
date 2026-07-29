"""
Transcription audio -> texte avec faster-whisper.

Différences majeures avec l'ancienne version :
- On utilise faster-whisper (CTranslate2) au lieu de la pipeline transformers :
  beaucoup plus rapide sur CPU comme sur GPU, moins gourmand en RAM.
- On charge le modèle "medium" par défaut (bien plus précis que "base"),
  avec repli automatique sur un modèle plus léger si la machine est trop juste.
- La segmentation en phrases est faite par le VAD (Voice Activity Detection)
  intégré à faster-whisper, donc les phrases ne sont plus jamais coupées
  au milieu comme avec le découpage vidéo fixe de 60s.
- Chaque segment garde ses timestamps de début/fin, essentiels pour
  resynchroniser l'audio traduit plus tard.
"""

from dataclasses import dataclass
from typing import List, Optional
from faster_whisper import WhisperModel


@dataclass
class SegmentTranscrit:
    debut: float          # secondes
    fin: float             # secondes
    texte: str
    langue_detectee: str


class Transcripteur:
    def __init__(self, taille_modele: str = "medium", device: str = "auto", compute_type: Optional[str] = None):
        """
        taille_modele: tiny, base, small, medium, large-v3
        device: "cpu", "cuda", ou "auto" (détecte le GPU si dispo)
        compute_type: précision de calcul. Par défaut on choisit intelligemment
                      selon le device (int8 sur CPU pour la vitesse, float16 sur GPU).
        """
        if device == "auto":
            device = self._detecter_device()

        if compute_type is None:
            compute_type = "float16" if device == "cuda" else "int8"

        print(f"[+] Chargement de faster-whisper ({taille_modele}, device={device}, compute={compute_type})...")
        self.modele = WhisperModel(taille_modele, device=device, compute_type=compute_type)

    @staticmethod
    def _detecter_device() -> str:
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            return "cpu"

    def transcrire(self, chemin_audio: str, langue_source: Optional[str] = None,
                    duree_totale: Optional[float] = None, on_segment=None) -> List[SegmentTranscrit]:
        """
        Transcrit un fichier audio complet en segments cohérents.

        langue_source: code langue ISO (ex: "fr"), ou None pour auto-détection.
        duree_totale: durée totale de l'audio en secondes, utilisée pour calculer
                      une progression en pourcentage au fur et à mesure.
        on_segment: callback optionnel appelé après chaque segment transcrit,
                    avec (temps_actuel, duree_totale) -- permet d'afficher une
                    progression en temps réel plutôt qu'un seul saut à 100%
                    à la toute fin (important sur les vidéos longues, où la
                    transcription peut prendre plusieurs dizaines de minutes
                    sur CPU sans aucun retour visuel sinon).
        """
        segments_iter, info = self.modele.transcribe(
            chemin_audio,
            language=langue_source,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 400},
            beam_size=5,
        )

        langue = info.language
        resultats = []
        for seg in segments_iter:
            texte = seg.text.strip()
            if texte:
                resultats.append(SegmentTranscrit(
                    debut=seg.start,
                    fin=seg.end,
                    texte=texte,
                    langue_detectee=langue,
                ))
            if on_segment:
                on_segment(seg.end, duree_totale)
        return resultats


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage : python transcriber.py chemin_audio.wav")
        sys.exit(1)

    t = Transcripteur(taille_modele="medium")
    segments = t.transcrire(sys.argv[1])
    for s in segments:
        print(f"[{s.debut:.1f}s -> {s.fin:.1f}s] ({s.langue_detectee}) {s.texte}")
