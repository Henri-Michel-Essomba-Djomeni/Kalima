"""
Traduction de texte avec NLLB-200 (Meta AI).

Pourquoi NLLB-200 plutôt que Helsinki-NLP/opus-mt :
- Un seul modèle gère 200 langues, dans toutes les directions.
  L'ancienne version devait recharger un modèle différent pour chaque
  paire de langues (fr-en, fr-es, etc.), ce qui n'aurait jamais tenu
  la route pour une app avec "langues changeables".
- Meilleure qualité de traduction générale, surtout sur du texte
  narratif/dialogue comme dans ton fichier de test.

Le modèle "distilled-600M" est un bon compromis vitesse/qualité pour
du CPU. On peut monter à "1.3B" ou "3.3B" si le matériel le permet.
"""

from typing import List, Optional
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer

# NLLB utilise des codes de langue spécifiques (FLORES-200), pas simplement "fr"/"en".
# On ne garde ici que les plus utiles ; la liste complète est facile à étendre.
CODES_LANGUES_NLLB = {
    "fr": "fra_Latn",
    "en": "eng_Latn",
    "es": "spa_Latn",
    "de": "deu_Latn",
    "it": "ita_Latn",
    "pt": "por_Latn",
    "ar": "arb_Arab",
    "zh": "zho_Hans",
    "ja": "jpn_Jpan",
    "ru": "rus_Cyrl",
}


class ErreurTraduction(Exception):
    pass


class Traducteur:
    def __init__(self, nom_modele: str = "facebook/nllb-200-distilled-600M", device: str = "cpu"):
        print(f"[+] Chargement du modèle de traduction {nom_modele}...")
        self.tokenizer = AutoTokenizer.from_pretrained(nom_modele)
        self.modele = AutoModelForSeq2SeqLM.from_pretrained(nom_modele)
        self.device = device
        self.modele.to(device)

    def _code_nllb(self, code_iso: str) -> str:
        if code_iso not in CODES_LANGUES_NLLB:
            raise ErreurTraduction(
                f"Langue '{code_iso}' non supportée. Langues dispo : {list(CODES_LANGUES_NLLB.keys())}"
            )
        return CODES_LANGUES_NLLB[code_iso]

    def traduire_texte(self, texte: str, langue_source: str, langue_cible: str) -> str:
        if not texte.strip():
            return ""

        code_src = self._code_nllb(langue_source)
        code_tgt = self._code_nllb(langue_cible)

        self.tokenizer.src_lang = code_src
        inputs = self.tokenizer(texte, return_tensors="pt").to(self.device)

        id_langue_cible = self.tokenizer.convert_tokens_to_ids(code_tgt)
        sortie = self.modele.generate(
            **inputs,
            forced_bos_token_id=id_langue_cible,
            max_length=512,
        )
        return self.tokenizer.batch_decode(sortie, skip_special_tokens=True)[0]

    def traduire_segments(self, textes: List[str], langue_source: str, langue_cible: str) -> List[str]:
        """Traduit une liste de segments un par un, en conservant l'ordre."""
        return [self.traduire_texte(t, langue_source, langue_cible) for t in textes]


if __name__ == "__main__":
    tr = Traducteur()
    resultat = tr.traduire_texte(
        "Il y a bien des années, notre chef a dû affronter le destructeur.",
        langue_source="fr",
        langue_cible="en",
    )
    print(resultat)
