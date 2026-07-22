"""
Clonage de voix avec OpenVoice v2 (MyShell AI).

Principe en deux temps :
1. MeloTTS génère la parole traduite avec une voix de base générique,
   dans la langue cible.
2. Le "Tone Color Converter" d'OpenVoice reprend cet audio et lui applique
   le timbre extrait de l'échantillon de la voix d'origine (voir
   voice_reference.py), sans jamais avoir eu besoin d'entraîner quoi que
   ce soit -- c'est ce qui rend l'approche rapide à mettre en place.

Licence : OpenVoice v2 est sous licence MIT (contrairement à XTTS-v2,
dont la licence interdit l'usage commercial) -- c'est le critère qui a
motivé ce choix pour un projet destiné à devenir un vrai produit.

Limite connue : MeloTTS (le moteur de base) ne couvre que l'anglais,
l'espagnol, le français, le chinois et le japonais pour l'instant. Pour
toute autre langue cible, ce module lève ErreurLangueNonClonable --
à charge du pipeline appelant de basculer sur la voix générique edge-tts.

Installation requise : voir la section "Clonage de la voix d'origine"
du README à la racine du projet -- l'installation a plusieurs étapes
(sous-dépendances de MeloTTS, dictionnaire unidic, ressource NLTK,
checkpoints OpenVoice) qui sont documentées en détail là-bas.
"""

import os
from typing import Optional

# Mapping langue cible (ISO) -> code langue MeloTTS
LANGUES_CLONABLES = {
    "en": "EN",
    "es": "ES",
    "fr": "FR",
    "zh": "ZH",
    "ja": "JP",
}


class ErreurLangueNonClonable(Exception):
    """Levée quand la langue cible n'est pas supportée par MeloTTS."""
    pass


class ErreurClonage(Exception):
    pass


class ClonageVoix:
    """
    Encapsule le pipeline OpenVoice complet. Les modèles sont lourds à
    charger (quelques secondes à quelques minutes selon le device) donc
    cette classe est faite pour être instanciée une seule fois et réutilisée.
    """

    def __init__(self, dossier_checkpoints: str = "checkpoints_v2", device: str = "cpu"):
        self.device = device
        self.dossier_checkpoints = dossier_checkpoints
        self._modeles_tts = {}   # cache par langue : {code_melo: instance TTS}
        self._convertisseur = None

    def _charger_convertisseur(self):
        if self._convertisseur is not None:
            return self._convertisseur

        try:
            from openvoice.api import ToneColorConverter
        except ImportError as e:
            raise ErreurClonage(
                f"Impossible d'importer OpenVoice ({e}). "
                "Il manque probablement une sous-dépendance. Voir le README."
            ) from e

        chemin_config = os.path.join(self.dossier_checkpoints, "converter", "config.json")
        chemin_ckpt = os.path.join(self.dossier_checkpoints, "converter", "checkpoint.pth")

        if not os.path.exists(chemin_config) or not os.path.exists(chemin_ckpt):
            raise ErreurClonage(
                f"Checkpoints OpenVoice introuvables dans '{self.dossier_checkpoints}'. "
                "Voir les instructions de téléchargement dans le README."
            )

        print("[+] Chargement du convertisseur de timbre OpenVoice...")
        convertisseur = ToneColorConverter(chemin_config, device=self.device)
        convertisseur.load_ckpt(chemin_ckpt)
        self._convertisseur = convertisseur
        print("[+] Convertisseur de timbre chargé.")
        return convertisseur

    def _charger_modele_tts(self, code_melo: str):
        if code_melo in self._modeles_tts:
            return self._modeles_tts[code_melo]

        try:
            from melo.api import TTS
        except ImportError as e:
            raise ErreurClonage(
                f"Impossible d'importer MeloTTS ({e}). "
                "Il manque probablement une sous-dépendance (installée normalement via --no-deps sautée). "
                "Voir le README."
            ) from e

        modele = TTS(language=code_melo, device=self.device)
        self._modeles_tts[code_melo] = modele
        print(f"[+] Modèle MeloTTS chargé pour '{code_melo}'.")
        return modele

    def generer_voix_clonee(
        self,
        texte: str,
        langue_cible: str,
        chemin_reference: str,
        chemin_sortie: str,
        vitesse: float = 1.0,
    ) -> str:
        """
        Génère un segment audio dans la langue cible, avec le timbre de
        chemin_reference appliqué dessus.
        """
        if langue_cible not in LANGUES_CLONABLES:
            raise ErreurLangueNonClonable(
                f"Le clonage n'est pas disponible pour '{langue_cible}'. "
                f"Langues clonables : {list(LANGUES_CLONABLES.keys())}"
            )

        if not texte.strip():
            raise ErreurClonage("Texte vide, rien à synthétiser.")

        import torch

        code_melo = LANGUES_CLONABLES[langue_cible]
        modele_tts = self._charger_modele_tts(code_melo)
        convertisseur = self._charger_convertisseur()

        os.makedirs(os.path.dirname(chemin_sortie) or ".", exist_ok=True)
        chemin_intermediaire = chemin_sortie + ".base.wav"

        # Étape 1 : synthèse vocale de base (voix générique dans la langue cible)
        speaker_ids = modele_tts.hps.data.spk2id
        premiere_voix = list(speaker_ids.values())[0]
        modele_tts.tts_to_file(texte, premiere_voix, chemin_intermediaire, speed=vitesse)

        # Étape 2 : extraction de l'empreinte vocale de la référence,
        # puis application de ce timbre sur l'audio généré à l'étape 1
        from openvoice import se_extractor

        cle_speaker = [k for k in speaker_ids.keys()][0]
        chemin_se_source = os.path.join(
            self.dossier_checkpoints, "base_speakers", "ses", f"{cle_speaker.lower()}.pth"
        )
        if not os.path.exists(chemin_se_source):
            raise ErreurClonage(f"Empreinte vocale de base introuvable : {chemin_se_source}")

        se_source = torch.load(chemin_se_source, map_location=self.device)
        se_cible, _ = se_extractor.get_se(chemin_reference, convertisseur, vad=True)

        convertisseur.convert(
            audio_src_path=chemin_intermediaire,
            src_se=se_source,
            tgt_se=se_cible,
            output_path=chemin_sortie,
        )

        if os.path.exists(chemin_intermediaire):
            os.remove(chemin_intermediaire)

        return chemin_sortie


def langue_est_clonable(langue_cible: str) -> bool:
    return langue_cible in LANGUES_CLONABLES
