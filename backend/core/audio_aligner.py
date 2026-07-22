"""
Construit la piste audio finale en plaçant chaque segment traduit
exactement à son timestamp d'origine, avec du silence entre les segments.

C'est ici qu'on résout un problème que l'ancienne version ignorait
complètement : une phrase traduite en anglais n'a jamais exactement
la même durée que la phrase française d'origine. Sans ajustement,
l'audio traduit se désynchronise progressivement de l'image.

Stratégie :
1. On génère l'audio du segment à vitesse normale.
2. On mesure sa durée réelle.
3. Si elle dépasse la fenêtre disponible (fin - début du segment
   d'origine), on régénère avec une vitesse légèrement accélérée
   (edge-tts supporte ça nativement, donc pas de perte de qualité
   comme avec un accéléré audio classique).
4. On place le résultat au bon timestamp dans la piste finale,
   avec du silence comblant les espaces.
"""

import os
from dataclasses import dataclass
from typing import List, Optional
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
    cloneur=None,
    chemin_reference: Optional[str] = None,
) -> SegmentAligne:
    """
    Génère l'audio d'un segment en ajustant sa vitesse pour qu'il tienne
    dans la fenêtre de temps [debut, fin] du segment vidéo d'origine.

    Si `cloneur` et `chemin_reference` sont fournis et que la langue cible
    est clonable, on génère avec la voix d'origine imitée. Sinon, on
    retombe automatiquement sur la voix générique edge-tts.
    """
    fenetre_ms = (fin - debut) * 1000
    chemin_sortie = os.path.join(dossier_temp, f"seg_{index:04d}.mp3")

    def _generer(vitesse_pourcentage: str):
        if cloneur is not None and chemin_reference is not None:
            from .voice_cloner import ErreurLangueNonClonable, ErreurClonage
            try:
                vitesse_ratio = 1.0 + (int(vitesse_pourcentage.strip('+%') or 0) / 100)
                cloneur.generer_voix_clonee(
                    texte, langue, chemin_reference, chemin_sortie, vitesse=vitesse_ratio
                )
                return
            except (ErreurLangueNonClonable, ErreurClonage) as e:
                print(f"[!] Segment {index} : repli sur la voix générique -- {e}")
        generer_voix(texte, langue, chemin_sortie, taux_vitesse=vitesse_pourcentage)

    # Première passe à vitesse normale
    _generer("+0%")
    duree_actuelle = _duree_fichier_ms(chemin_sortie)

    if duree_actuelle > fenetre_ms and fenetre_ms > 0:
        ratio_necessaire = duree_actuelle / fenetre_ms
        ratio_applique = min(ratio_necessaire, marge_max_acceleration)
        pourcentage = int((ratio_applique - 1) * 100)
        _generer(f"+{pourcentage}%")

    return SegmentAligne(debut=debut, fin=fin, chemin_audio=chemin_sortie)


def construire_piste_audio_complete(
    segments: List[SegmentAligne],
    duree_totale_secondes: float,
    chemin_sortie: str,
) -> str:
    """
    Assemble tous les segments audio calibrés en une seule piste,
    chacun placé exactement à son timestamp d'origine.
    """
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
