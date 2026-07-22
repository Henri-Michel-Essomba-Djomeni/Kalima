"""
Sélectionne et extrait un échantillon de la voix d'origine, à partir des
segments déjà transcrits, pour servir de référence au clonage vocal.

Stratégie : plutôt que de prendre bêtement les 10 premières secondes
(qui peuvent tomber sur un silence ou un bruit de fond), on choisit le
ou les segments de parole les plus longs et les plus continus détectés
par Whisper -- ils ont statistiquement plus de chances d'être de la
parole propre, sans coupure ni superposition.
"""

import os
from typing import List
from pydub import AudioSegment

from .transcriber import SegmentTranscrit


def extraire_echantillon_reference(
    chemin_audio_source: str,
    segments: List[SegmentTranscrit],
    chemin_sortie: str,
    duree_cible_secondes: float = 12.0,
) -> str:
    """
    Construit un échantillon audio de référence en concaténant les segments
    de parole les plus longs, jusqu'à atteindre ~duree_cible_secondes.

    Retourne le chemin du fichier de référence généré.
    """
    if not segments:
        raise ValueError("Aucun segment transcrit disponible pour extraire une voix de référence.")

    # On trie par durée décroissante : les segments longs sont ceux où la
    # personne parle en continu, donc les plus fiables comme empreinte vocale.
    segments_tries = sorted(segments, key=lambda s: s.fin - s.debut, reverse=True)

    audio_complet = AudioSegment.from_file(chemin_audio_source)
    echantillon = AudioSegment.empty()
    duree_accumulee = 0.0

    for seg in segments_tries:
        if duree_accumulee >= duree_cible_secondes:
            break
        debut_ms = int(seg.debut * 1000)
        fin_ms = int(seg.fin * 1000)
        echantillon += audio_complet[debut_ms:fin_ms]
        duree_accumulee += (seg.fin - seg.debut)

    os.makedirs(os.path.dirname(chemin_sortie) or ".", exist_ok=True)
    echantillon.export(chemin_sortie, format="wav")
    return chemin_sortie
