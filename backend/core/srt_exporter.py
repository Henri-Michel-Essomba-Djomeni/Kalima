"""
Export de segments transcrits/traduits vers SRT et VTT.
"""

import os
import json
from typing import List, Optional


def _timestamp_srt(secondes: float) -> str:
    h = int(secondes // 3600)
    m = int((secondes % 3600) // 60)
    s = int(secondes % 60)
    ms = int((secondes - int(secondes)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _timestamp_vtt(secondes: float) -> str:
    h = int(secondes // 3600)
    m = int((secondes % 3600) // 60)
    s = int(secondes % 60)
    ms = int((secondes - int(secondes)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def segments_vers_srt(segments: List[dict]) -> str:
    lignes = []
    for i, seg in enumerate(segments, 1):
        afficher = seg.get("traduction") or seg.get("texte_original", "")
        if not afficher.strip():
            continue
        lignes.append(str(i))
        lignes.append(
            f"{_timestamp_srt(seg['debut'])} --> {_timestamp_srt(seg['fin'])}"
        )
        lignes.append(afficher)
        lignes.append("")
    return "\n".join(lignes)


def segments_vers_vtt(segments: List[dict]) -> str:
    lignes = ["WEBVTT", ""]
    for i, seg in enumerate(segments, 1):
        afficher = seg.get("traduction") or seg.get("texte_original", "")
        if not afficher.strip():
            continue
        lignes.append(
            f"{_timestamp_vtt(seg['debut'])} --> {_timestamp_vtt(seg['fin'])}"
        )
        lignes.append(afficher)
        lignes.append("")
    return "\n".join(lignes)


def segments_vers_texte(segments: List[dict]) -> str:
    return "\n".join(
        seg.get("traduction") or seg.get("texte_original", "")
        for seg in segments
        if (seg.get("traduction") or seg.get("texte_original", "")).strip()
    )


def charger_transcription(chemin_json: str) -> Optional[List[dict]]:
    if not os.path.exists(chemin_json):
        return None
    with open(chemin_json, "r", encoding="utf-8") as f:
        return json.load(f)
