"""
Orchestrateur du pipeline complet de traduction vidéo.

Enchaîne : extraction audio -> transcription -> traduction -> génération
voix calibrée par segment -> assemblage final. Expose une fonction de
progression (callback) pour qu'une interface (web ou autre) puisse
afficher une barre d'avancement en temps réel.
"""

import os
import tempfile
import shutil
from dataclasses import dataclass
from typing import Callable, Optional

from .audio_extractor import extraire_audio
from .transcriber import Transcripteur
from .translator import Traducteur
from .audio_aligner import generer_segment_calibre, construire_piste_audio_complete
from .video_assembler import assembler_video_finale
from .audio_extractor import obtenir_duree_video


@dataclass
class ProgressionEtape:
    etape: str          # "extraction", "transcription", "traduction", "voix", "assemblage"
    pourcentage: float  # 0-100 dans l'étape
    message: str


TypeCallback = Optional[Callable[[ProgressionEtape], None]]


class PipelineTraduction:
    def __init__(self, taille_modele_whisper: str = "medium"):
        # Les modèles sont chargés une seule fois et réutilisés pour tous les jobs
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
            # --- 1. Extraction audio ---
            notifier("extraction", 0, "Extraction de la piste audio...")
            chemin_audio = os.path.join(dossier_temp, "audio_source.wav")
            extraire_audio(chemin_video, chemin_audio)
            duree_totale = obtenir_duree_video(chemin_video)
            notifier("extraction", 100, "Audio extrait.")

            # --- 2. Transcription ---
            # On laisse Whisper détecter la langue automatiquement plutôt que
            # de forcer la langue indiquée par l'utilisateur : si jamais il y a
            # une erreur de manipulation (langues inversées, mauvais code...),
            # la détection auto évite de transcrire l'audio dans la mauvaise langue.
            notifier("transcription", 0, "Transcription en cours (peut prendre du temps sur une vidéo longue)...")
            transcripteur = self._get_transcripteur()
            segments = transcripteur.transcrire(chemin_audio, langue_source=None)
            notifier("transcription", 100, f"{len(segments)} segments transcrits.")

            if segments and segments[0].langue_detectee != langue_source:
                notifier(
                    "transcription", 100,
                    f"ATTENTION : langue détectée dans la vidéo = '{segments[0].langue_detectee}', "
                    f"mais tu as indiqué '{langue_source}'. La transcription utilise la langue détectée."
                )
                langue_source = segments[0].langue_detectee

            if not segments:
                raise RuntimeError("Aucune parole détectée dans la vidéo.")

            # --- 3. Traduction ---
            notifier("traduction", 0, "Traduction des segments...")
            traducteur = self._get_traducteur()
            textes_traduits = []
            for i, seg in enumerate(segments):
                texte_traduit = traducteur.traduire_texte(seg.texte, langue_source, langue_cible)
                textes_traduits.append(texte_traduit)
                notifier("traduction", (i + 1) / len(segments) * 100, f"Segment {i+1}/{len(segments)} traduit.")

            # --- 4. Génération voix calibrée par segment ---
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
                notifier("voix", (i + 1) / len(segments) * 100, f"Voix générée {i+1}/{len(segments)}.")

            chemin_piste_audio = os.path.join(dossier_temp, "piste_finale.mp3")
            construire_piste_audio_complete(segments_alignes, duree_totale, chemin_piste_audio)

            # --- 5. Assemblage final ---
            notifier("assemblage", 0, "Assemblage de la vidéo finale...")
            assembler_video_finale(chemin_video, chemin_piste_audio, chemin_sortie)
            notifier("assemblage", 100, "Terminé !")

            return chemin_sortie

        finally:
            shutil.rmtree(dossier_temp, ignore_errors=True)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage : python pipeline.py video.mp4 langue_source langue_cible")
        print("Exemple : python pipeline.py film.mp4 fr en")
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
