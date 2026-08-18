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
from .voice_reference import extraire_echantillon_reference
from .voice_cloner import ClonageVoix, langue_est_clonable
from .srt_exporter import segments_vers_srt, segments_vers_texte
from .subtitle_embedder import incruster_sous_titres
from .resumeur import resumer_texte
from .transcription_cache import calculer_empreinte, lire_cache, ecrire_cache


@dataclass
class ProgressionEtape:
    etape: str
    pourcentage: float
    message: str


TypeCallback = Optional[Callable[[ProgressionEtape], None]]

# Modes disponibles :
#  - "doublage"     : pipeline complet, voix traduite + vidéo finale (comportement historique)
#  - "sous_titres"  : transcription + traduction, incrustées en piste texte, AUDIO JAMAIS TOUCHÉ
#  - "transcription": transcription (+ traduction si langues différentes), export texte seul
#  - "resume"       : transcription + traduction + résumé via LLM (Ollama), export texte seul
MODES_VALIDES = {"doublage", "sous_titres", "transcription", "resume"}


class PipelineTraduction:
    def __init__(self, taille_modele_whisper: str = "medium"):
        self._transcripteur: Optional[Transcripteur] = None
        self._traducteur: Optional[Traducteur] = None
        self._cloneur: Optional[ClonageVoix] = None
        self.taille_modele_whisper = taille_modele_whisper

    def _get_transcripteur(self) -> Transcripteur:
        if self._transcripteur is None:
            self._transcripteur = Transcripteur(taille_modele=self.taille_modele_whisper)
        return self._transcripteur

    def _get_traducteur(self) -> Traducteur:
        if self._traducteur is None:
            self._traducteur = Traducteur()
        return self._traducteur

    def _get_cloneur(self) -> ClonageVoix:
        if self._cloneur is None:
            self._cloneur = ClonageVoix()
        return self._cloneur

    def executer(
        self,
        chemin_video: str,
        langue_source: str,
        langue_cible: str,
        chemin_sortie: str,
        on_progress: TypeCallback = None,
        cloner_voix: bool = False,
        mode: str = "doublage",
        marquage: bool = True,
    ) -> str:
        if mode not in MODES_VALIDES:
            raise ValueError(f"Mode inconnu : '{mode}'. Valides : {MODES_VALIDES}")

        def notifier(etape, pct, msg):
            if on_progress:
                on_progress(ProgressionEtape(etape=etape, pourcentage=pct, message=msg))

        dossier_temp = tempfile.mkdtemp(prefix="videotrans_")
        try:
            # --- Étapes communes à tous les modes : extraction + transcription ---
            notifier("extraction", 0, "Extraction de la piste audio...")
            chemin_audio = os.path.join(dossier_temp, "audio_source.wav")
            extraire_audio(chemin_video, chemin_audio)
            duree_totale = obtenir_duree_video(chemin_video)
            notifier("extraction", 100, "Audio extrait.")

            notifier("transcription", 0, "Vérification de la mémoire (empreinte de la vidéo)...")
            empreinte = calculer_empreinte(chemin_video)
            segments = lire_cache(empreinte)

            if segments:
                notifier(
                    "transcription", 100,
                    f"{len(segments)} segments récupérés de la mémoire -- cette vidéo a déjà été transcrite récemment."
                )
            else:
                transcripteur = self._get_transcripteur()

                def on_segment(temps_actuel, duree_totale_audio):
                    if duree_totale_audio:
                        pct = min(temps_actuel / duree_totale_audio * 100, 99)
                        notifier("transcription", pct, f"{temps_actuel:.0f}s / {duree_totale_audio:.0f}s transcrits...")

                segments = transcripteur.transcrire(
                    chemin_audio, langue_source=None,
                    duree_totale=duree_totale, on_segment=on_segment,
                )
                notifier("transcription", 100, f"{len(segments)} segments transcrits.")
                ecrire_cache(empreinte, segments)

            if segments and segments[0].langue_detectee != langue_source:
                notifier(
                    "transcription", 100,
                    f"Langue détectée = '{segments[0].langue_detectee}', "
                    f"utilisateur indique '{langue_source}'. Utilisation de la détection auto."
                )
                langue_source = segments[0].langue_detectee

            if not segments:
                raise RuntimeError("Aucune parole détectée dans la vidéo.")

            # --- Traduction (commune à tous les modes sauf si les langues
            # sont identiques, auquel cas ça n'aurait aucun sens) ---
            besoin_traduction = langue_source != langue_cible
            notifier("traduction", 0, "Traduction des segments..." if besoin_traduction else "Langues identiques, pas de traduction nécessaire.")
            traducteur = self._get_traducteur() if besoin_traduction else None
            textes_traduits = []
            donnees_segments = []
            for i, seg in enumerate(segments):
                texte_traduit = traducteur.traduire_texte(seg.texte, langue_source, langue_cible) if besoin_traduction else seg.texte
                textes_traduits.append(texte_traduit)
                donnees_segments.append({
                    "index": i,
                    "debut": seg.debut,
                    "fin": seg.fin,
                    "texte_original": seg.texte,
                    "traduction": texte_traduit,
                })
                notifier("traduction", (i + 1) / len(segments) * 100, f"Segment {i+1}/{len(segments)} traité.")

            chemin_json = None
            if chemin_sortie.endswith(".mp4"):
                chemin_json = chemin_sortie.replace(".mp4", "_transcription.json")
            self._ecrire_json_transcription(chemin_json, langue_source, langue_cible, donnees_segments)

            # ================= MODE : TRANSCRIPTION SEULE =================
            if mode == "transcription":
                notifier("voix", 100, "Mode transcription seule -- pas de génération vocale.")
                notifier("assemblage", 100, "Transcription prête.")
                texte_final = segments_vers_texte(donnees_segments)
                with open(chemin_sortie, "w", encoding="utf-8") as f:
                    f.write(texte_final)
                return chemin_sortie

            # ================= MODE : RÉSUMÉ =================
            if mode == "resume":
                notifier("voix", 30, "Génération du résumé (Ollama)...")
                texte_complet = " ".join(s["traduction"] for s in donnees_segments)
                resume = resumer_texte(texte_complet, langue=langue_cible)
                notifier("voix", 100, "Résumé généré.")
                notifier("assemblage", 100, "Résumé prêt.")
                with open(chemin_sortie, "w", encoding="utf-8") as f:
                    f.write(resume)
                return chemin_sortie

            # ================= MODE : SOUS-TITRES SEULS =================
            if mode == "sous_titres":
                notifier("voix", 100, "Mode sous-titres seuls -- audio d'origine conservé tel quel.")
                notifier("assemblage", 0, "Incrustation des sous-titres...")
                chemin_srt = os.path.join(dossier_temp, "sous_titres.srt")
                with open(chemin_srt, "w", encoding="utf-8") as f:
                    f.write(segments_vers_srt(donnees_segments))
                incruster_sous_titres(chemin_video, chemin_srt, chemin_sortie, marquage=marquage)
                notifier("assemblage", 100, "Terminé !")
                return chemin_sortie

            # ================= MODE : DOUBLAGE COMPLET (par défaut) =================
            cloneur = None
            chemin_reference = None
            if cloner_voix and langue_est_clonable(langue_cible):
                notifier("voix", 0, "Extraction d'un échantillon de la voix d'origine...")
                chemin_reference = os.path.join(dossier_temp, "voix_reference.wav")
                extraire_echantillon_reference(chemin_audio, segments, chemin_reference)
                cloneur = self._get_cloneur()
            elif cloner_voix:
                notifier(
                    "voix", 0,
                    f"Le clonage n'est pas disponible pour '{langue_cible}' -- voix Kokoro générique utilisée."
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
                        cloneur=cloneur,
                        chemin_reference=chemin_reference,
                    )
                    segments_alignes.append(seg_aligne)
                notifier("voix", (i + 1) / len(segments) * 100, f"Voix générée {i+1}/{len(segments)}.")

            chemin_piste_audio = os.path.join(dossier_temp, "piste_finale.mp3")
            construire_piste_audio_complete(segments_alignes, duree_totale, chemin_piste_audio)

            notifier("assemblage", 0, "Assemblage de la vidéo finale...")
            assembler_video_finale(chemin_video, chemin_piste_audio, chemin_sortie, marquage=marquage)
            notifier("assemblage", 100, "Terminé !")

            return chemin_sortie
        finally:
            shutil.rmtree(dossier_temp, ignore_errors=True)

    @staticmethod
    def _ecrire_json_transcription(chemin_json, langue_source, langue_cible, donnees_segments):
        if not chemin_json:
            return
        with open(chemin_json, "w", encoding="utf-8") as f:
            json.dump({
                "langue_source": langue_source,
                "langue_cible": langue_cible,
                "segments": donnees_segments,
            }, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 4:
        print("Usage : python pipeline.py video.mp4 langue_source langue_cible [--cloner-voix] [--mode=doublage|sous_titres|transcription|resume]")
        sys.exit(1)

    def afficher_progres(p: ProgressionEtape):
        print(f"[{p.etape}] {p.pourcentage:.0f}% - {p.message}")

    mode_choisi = "doublage"
    for arg in sys.argv:
        if arg.startswith("--mode="):
            mode_choisi = arg.split("=", 1)[1]

    extension = ".mp4" if mode_choisi in ("doublage", "sous_titres") else ".txt"

    pipeline = PipelineTraduction()
    resultat = pipeline.executer(
        chemin_video=sys.argv[1],
        langue_source=sys.argv[2],
        langue_cible=sys.argv[3],
        chemin_sortie=f"resultat_kalima{extension}",
        on_progress=afficher_progres,
        cloner_voix="--cloner-voix" in sys.argv,
        mode=mode_choisi,
    )
    print(f"Résultat : {resultat}")