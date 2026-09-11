"""
Extrait le bloc d'action caché de la réponse du modèle.

Le modèle termine parfois sa réponse par :
    §ACTION§{"mode": "...", "target_lang": "...", ...}§FIN§

Ce module sépare ce bloc du texte visible, pour que le frontend
n'affiche jamais que la réponse normale, et utilise le JSON pour
pré-remplir le formulaire.
"""

import json
import re

_ACTION_PATTERN = re.compile(r"§ACTION§(.*?)§FIN§", re.DOTALL)


def extract_action(raw_reply: str) -> tuple[str, dict | None]:
    """
    Retourne (texte_visible, action_dict_ou_None).
    En cas de JSON malformé dans le bloc, on l'ignore silencieusement
    plutôt que de faire planter la réponse à l'utilisateur.
    """
    match = _ACTION_PATTERN.search(raw_reply)

    if not match:
        return raw_reply.strip(), None

    visible_text = _ACTION_PATTERN.sub("", raw_reply).strip()

    action = None
    try:
        action = json.loads(match.group(1))
        # On ne garde que les champs non nuls, pour un JSON propre côté frontend
        action = {k: v for k, v in action.items() if v is not None}
        if not action:
            action = None
    except (json.JSONDecodeError, AttributeError):
        action = None

    return visible_text, action
