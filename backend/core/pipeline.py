import os
import tempfile
import shutil
import json
from dataclasses import dataclass
from typing import Callable, Optional

from .audio_extractor import extraire_audio, obtenir_duree_video
from .transcriber import Transcripteur
from .translator import Traducteur
from .audio_aligner import generer_segment_calibre, construire_piste_audio_complete
from .video_assembler import assembler_video_finale


@dataclass
class ProgressionEtape:
    etape: str
    pourcentage: float
    message: str


TypeCallback = Optional[Callable[[ProgressionEtape], None]]


class PipelineTraduction:
    def __init__(self, taille_modele_whisper: str = "medium"):
        self._transcripteur: Optional[Transcripteur] = None
        self._traducteur: Optional[Traducteur] = None
        self.taille_modele_whisper = taille_modele_whisper

    def _get_transcripteur(self) -> Transcripteur:
        if self._transcripteur is None:
            self._transcripteur = Transcripteur(taille_modele=self.taille_modele_whisper)
        return self._transcripteur

    def _get_traducteur(self) -> Traducteur:
        if self._traducteur is None:
            self._traducteur = Traducteur()
        return self._traducteur

    def executer(
        self,
        chemin_video: str,
        langue_source: str,
        langue_cible: str,
        chemin_sortie: str,
        on_progress: TypeCallback = None,
    ) -> str:
        def notifier(etape, pct, msg):
            if on_progress:
                on_progress(ProgressionEtape(etape=etape, pourcentage=pct, message=msg))

        dossier_temp = tempfile.mkdtemp(prefix="videotrans_")
        try:
            notifier("extraction", 0, "Extraction de la piste audio...")
            chemin_audio = os.path.join(dossier_temp, "audio_source.wav")
            extraire_audio(chemin_video, chemin_audio)
            duree_totale = obtenir_duree_video(chemin_video)
            notifier("extraction", 100, "Audio extrait.")

            notifier("transcription", 0, "Transcription en cours...")
            transcripteur = self._get_transcripteur()
            segments = transcripteur.transcrire(chemin_audio, langue_source=None)
            notifier("transcription", 100, f"{len(segments)} segments transcrits.")

            if segments and segments[0].langue_detectee != langue_source:
                notifier(
                    "transcription", 100,
                    f"Langue détectée = '{segments[0].langue_detectee}', "
                    f"utilisateur indique '{langue_source}'. Utilisation de la détection auto."
                )
                langue_source = segments[0].langue_detectee

            if not segments:
                raise RuntimeError("Aucune parole détectée dans la vidéo.")

            notifier("traduction", 0, "Traduction des segments...")
            traducteur = self._get_traducteur()
            textes_traduits = []
            donnees_segments = []
            for i, seg in enumerate(segments):
                texte_traduit = traducteur.traduire_texte(
                    seg.texte, langue_source, langue_cible
                )
                textes_traduits.append(texte_traduit)
                donnees_segments.append({
                    "index": i,
                    "debut": seg.debut,
                    "fin": seg.fin,
                    "texte_original": seg.texte,
                    "traduction": texte_traduit,
                })
                notifier(
                    "traduction",
                    (i + 1) / len(segments) * 100,
                    f"Segment {i+1}/{len(segments)} traduit.",
                )

            notifier("voix", 0, "Génération de la voix traduite...")
            dossier_audio_segments = os.path.join(dossier_temp, "segments_audio")
            os.makedirs(dossier_audio_segments, exist_ok=True)
            segments_alignes = []
            for i, (seg, texte_tr) in enumerate(zip(segments, textes_traduits)):
                if texte_tr.strip():
                    seg_aligne = generer_segment_calibre(
                        texte=texte_tr,
                        langue=langue_cible,
                        debut=seg.debut,
                        fin=seg.fin,
                        dossier_temp=dossier_audio_segments,
                        index=i,
                    )
                    segments_alignes.append(seg_aligne)
                notifier(
                    "voix",
                    (i + 1) / len(segments) * 100,
                    f"Voix générée {i+1}/{len(segments)}.",
                )

            chemin_piste_audio = os.path.join(dossier_temp, "piste_finale.mp3")
            construire_piste_audio_complete(
                segments_alignes, duree_totale, chemin_piste_audio
            )

            notifier("assemblage", 0, "Assemblage de la vidéo finale...")
            assembler_video_finale(chemin_video, chemin_piste_audio, chemin_sortie)
            notifier("assemblage", 100, "Terminé !")

            chemin_json = chemin_sortie.replace(".mp4", "_transcription.json")
            with open(chemin_json, "w", encoding="utf-8") as f:
                json.dump({
                    "langue_source": langue_source,
                    "langue_cible": langue_cible,
                    "segments": donnees_segments,
                }, f, ensure_ascii=False, indent=2)

            return chemin_sortie
        finally:
            shutil.rmtree(dossier_temp, ignore_errors=True)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage : python pipeline.py video.mp4 langue_source langue_cible")
        sys.exit(1)

    def afficher_progres(p: ProgressionEtape):
        print(f"[{p.etape}] {p.pourcentage:.0f}% - {p.message}")

    pipeline = PipelineTraduction()
    resultat = pipeline.executer(
        chemin_video=sys.argv[1],
        langue_source=sys.argv[2],
        langue_cible=sys.argv[3],
        chemin_sortie="video_traduite_finale.mp4",
        on_progress=afficher_progres,
    )
    print(f"Vidéo finale : {resultat}")
