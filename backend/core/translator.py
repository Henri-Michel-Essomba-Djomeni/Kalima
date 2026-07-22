"""
Traduction de texte avec M2M-100 (Meta AI) — licence MIT.

Pourquoi M2M-100 plutôt que NLLB-200 :
- M2M-100 est sous licence MIT (usage commercial libre).
- NLLB-200 est sous CC BY-NC 4.0 (interdit en commercial).
- M2M-100 couvre 100 langues, dans toutes les directions.
- Qualité comparable sur la plupart des paires de langues courantes.
- Même API Transformers, migration transparente.

Modèle 418M : bon compromis vitesse/qualité sur CPU.
Modèle 1.2B : meilleure qualité, plus de mémoire.
"""

from typing import List, Optional
from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer

# Codes langue M2M-100 (ISO 639-1 → code interne M2M).
# La liste complète fait ~100 langues ; on expose les plus utiles.
CODES_LANGUES_M2M = {
    "fr": "fr",
    "en": "en",
    "es": "es",
    "de": "de",
    "it": "it",
    "pt": "pt",
    "ar": "ar",
    "zh": "zh",
    "ja": "ja",
    "ru": "ru",
}


class ErreurTraduction(Exception):
    pass


class Traducteur:
    def __init__(self, nom_modele: str = "facebook/m2m100_418M", device: str = "cpu"):
        print(f"[+] Chargement du modèle de traduction {nom_modele}...")
        self.tokenizer = M2M100Tokenizer.from_pretrained(nom_modele)
        self.modele = M2M100ForConditionalGeneration.from_pretrained(nom_modele)
        self.device = device
        self.modele.to(device)

    def _verifier_langue(self, code_iso: str) -> None:
        if code_iso not in CODES_LANGUES_M2M:
            raise ErreurTraduction(
                f"Langue '{code_iso}' non supportée. "
                f"Langues dispo : {list(CODES_LANGUES_M2M.keys())}"
            )

    def traduire_texte(self, texte: str, langue_source: str, langue_cible: str) -> str:
        if not texte.strip():
            return ""

        self._verifier_langue(langue_source)
        self._verifier_langue(langue_cible)

        self.tokenizer.src_lang = langue_source
        inputs = self.tokenizer(texte, return_tensors="pt").to(self.device)

        id_langue_cible = self.tokenizer.lang_code_to_id[langue_cible]
        sortie = self.modele.generate(
            **inputs,
            forced_bos_token_id=id_langue_cible,
            max_length=512,
        )
        return self.tokenizer.batch_decode(sortie, skip_special_tokens=True)[0]

    def traduire_segments(self, textes: List[str], langue_source: str, langue_cible: str) -> List[str]:
        return [self.traduire_texte(t, langue_source, langue_cible) for t in textes]


if __name__ == "__main__":
    tr = Traducteur()
    resultat = tr.traduire_texte(
        "Il y a bien des années, notre chef a dû affronter le destructeur.",
        langue_source="fr",
        langue_cible="en",
    )
    print(resultat)
