"""
Construit la piste audio finale en plaçant chaque segment traduit
exactement à son timestamp d'origine, avec du silence entre les segments.

Stratégie :
1. Génération de l'audio du segment à vitesse normale via Piper TTS.
2. Mesure de la durée réelle.
3. Si elle dépasse la fenêtre disponible (fin - début du segment
   d'origine), on régénère avec une vitesse légèrement accélérée.
4. Placement du résultat au bon timestamp dans la piste finale,
   avec du silence comblant les espaces.
"""

import os
from dataclasses import dataclass
from typing import List
from pydub import AudioSegment

from .tts_generator import generer_voix, ErreurTTS


@dataclass
class SegmentAligne:
    debut: float
    fin: float
    chemin_audio: str


def _duree_fichier_ms(chemin: str) -> int:
    return len(AudioSegment.from_file(chemin))


def generer_segment_calibre(
    texte: str,
    langue: str,
    debut: float,
    fin: float,
    dossier_temp: str,
    index: int,
    marge_max_acceleration: float = 1.4,
) -> SegmentAligne:
    fenetre_ms = (fin - debut) * 1000
    chemin_sortie = os.path.join(dossier_temp, f"seg_{index:04d}.wav")

    generer_voix(texte, langue, chemin_sortie, taux_vitesse="+0%")
    duree_actuelle = _duree_fichier_ms(chemin_sortie)

    if duree_actuelle > fenetre_ms > 0:
        ratio_necessaire = duree_actuelle / fenetre_ms
        ratio_applique = min(ratio_necessaire, marge_max_acceleration)
        pourcentage = int((ratio_applique - 1) * 100)
        generer_voix(texte, langue, chemin_sortie, taux_vitesse=f"+{pourcentage}%")

    return SegmentAligne(debut=debut, fin=fin, chemin_audio=chemin_sortie)


def construire_piste_audio_complete(
    segments: List[SegmentAligne],
    duree_totale_secondes: float,
    chemin_sortie: str,
) -> str:
    piste_finale = AudioSegment.silent(duration=int(duree_totale_secondes * 1000))

    for seg in segments:
        if not os.path.exists(seg.chemin_audio):
            continue
        audio_segment = AudioSegment.from_file(seg.chemin_audio)
        position_ms = int(seg.debut * 1000)
        piste_finale = piste_finale.overlay(audio_segment, position=position_ms)

    os.makedirs(os.path.dirname(chemin_sortie) or ".", exist_ok=True)
    piste_finale.export(chemin_sortie, format="mp3")
    return chemin_sortie
