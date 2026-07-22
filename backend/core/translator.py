"""
Traduction de texte avec deux backends :
1. Ollama (Qwen 3, licence Apache 2.0) — prioritaire, qualité supérieure
2. M2M-100 (Meta, licence MIT) — fallback automatique si Ollama indisponible

Stratégie :
- Au premier appel, on détecte si Ollama est accessible.
- Si oui → on utilise Qwen 3 (modèle LLM local, 100+ langues).
- Si non → fallback silencieux vers M2M-100 (10 langues, plus léger).
- L'utilisateur peut forcer un backend avec FORCE_TRADUCTEUR=ollama|m2m.
"""

import os
from typing import List, Optional

from transformers import M2M100ForConditionalGeneration, M2M100Tokenizer


CODES_LANGUES_M2M = {
    "fr": "fr", "en": "en", "es": "es",
    "de": "de", "it": "it", "pt": "pt",
    "ar": "ar", "zh": "zh", "ja": "ja", "ru": "ru",
}

CODES_LANGUES_OLLAMA = {
    "fr": "French", "en": "English", "es": "Spanish",
    "de": "German", "it": "Italian", "pt": "Portuguese",
    "ar": "Arabic", "zh": "Chinese", "ja": "Japanese",
    "ru": "Russian", "nl": "Dutch", "pl": "Polish",
    "tr": "Turkish", "vi": "Vietnamese", "th": "Thai",
    "hi": "Hindi", "ko": "Korean",
}

CODES_LANGUES = {**CODES_LANGUES_M2M, **CODES_LANGUES_OLLAMA}

URL_OLLAMA = os.environ.get("OLLAMA_URL", "http://localhost:11434")
MODELE_OLLAMA = os.environ.get("OLLAMA_MODELE", "qwen3:7b")
_M2M_NOM_MODELE = "facebook/m2m100_418M"


class ErreurTraduction(Exception):
    pass


def ollama_disponible() -> bool:
    try:
        import ollama
        ollama.Client(host=URL_OLLAMA).list()
        return True
    except Exception:
        return False


class TraducteurOllama:
    def __init__(self):
        import ollama
        self._client = ollama.Client(host=URL_OLLAMA)
        self._modele = MODELE_OLLAMA

    def traduire(self, texte: str, langue_source: str, langue_cible: str) -> str:
        if not texte.strip():
            return ""
        nom_src = CODES_LANGUES_OLLAMA.get(langue_source, langue_source)
        nom_dst = CODES_LANGUES_OLLAMA.get(langue_cible, langue_cible)
        prompt = (
            f"Translate from {nom_src} to {nom_dst}. "
            f"Output ONLY the translation:\n\n{texte}"
        )
        rep = self._client.generate(model=self._modele, prompt=prompt)
        return rep.response.strip()


class TraducteurM2M:
    def __init__(self):
        self.tokenizer = M2M100Tokenizer.from_pretrained(_M2M_NOM_MODELE)
        self.modele = M2M100ForConditionalGeneration.from_pretrained(_M2M_NOM_MODELE)
        self.device = "cpu"
        self.modele.to(self.device)

    def traduire(self, texte: str, langue_source: str, langue_cible: str) -> str:
        if not texte.strip():
            return ""
        self.tokenizer.src_lang = langue_source
        inputs = self.tokenizer(texte, return_tensors="pt").to(self.device)
        id_cible = self.tokenizer.lang_code_to_id[langue_cible]
        sortie = self.modele.generate(
            **inputs, forced_bos_token_id=id_cible, max_length=512
        )
        return self.tokenizer.batch_decode(sortie, skip_special_tokens=True)[0]


class Traducteur:
    def __init__(self):
        self._ollama: Optional[TraducteurOllama] = None
        self._m2m: Optional[TraducteurM2M] = None
        force = os.environ.get("FORCE_TRADUCTEUR", "").lower()

        if force == "m2m":
            print("[+] Traduction : backend M2M-100 forcé.")
            self._m2m = TraducteurM2M()
        elif force == "ollama":
            if ollama_disponible():
                print("[+] Traduction : backend Ollama forcé.")
                self._ollama = TraducteurOllama()
            else:
                raise ErreurTraduction("Ollama forcé mais indisponible.")
        else:
            if ollama_disponible():
                print("[+] Traduction : backend Ollama (Qwen 3).")
                self._ollama = TraducteurOllama()
            else:
                print("[+] Traduction : backend M2M-100 (fallback).")
                self._m2m = TraducteurM2M()

    def traduire_texte(self, texte: str, langue_source: str, langue_cible: str) -> str:
        if self._ollama:
            return self._ollama.traduire(texte, langue_source, langue_cible)
        return self._m2m.traduire(texte, langue_source, langue_cible)

    def traduire_segments(
        self, textes: List[str], langue_source: str, langue_cible: str
    ) -> List[str]:
        return [self.traduire_texte(t, langue_source, langue_cible) for t in textes]


if __name__ == "__main__":
    tr = Traducteur()
    r = tr.traduire_texte(
        "Il y a bien des années, notre chef a dû affronter le destructeur.",
        langue_source="fr", langue_cible="en",
    )
    print(r)
