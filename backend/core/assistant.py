"""
Assistant conversationnel de Kalima -- LLM local (Ollama / Qwen), même
modèle que celui déjà utilisé pour le résumé (core/resumeur.py).

Deux rôles :
1. Accueillir, expliquer, vendre l'app -- disponible même avant connexion.
2. Piloter le formulaire en langage naturel : quand l'utilisateur exprime
   une intention claire, la réponse se termine par un bloc caché
   §ACTION§{...}§FIN§ que ce module extrait avant de renvoyer la réponse.
   L'assistant ne lance jamais rien lui-même -- il ne fait que proposer
   un réglage ; c'est toujours l'utilisateur qui dépose la vidéo et
   clique sur "Lancer".
"""

import json
import re

from .translator import ollama_disponible, URL_OLLAMA, MODELE_OLLAMA


class ErreurAssistant(Exception):
    pass


_MOTIF_ACTION = re.compile(r"§ACTION§(.*?)§FIN§", re.DOTALL)

PROMPT_SYSTEME = """Tu es l'assistant intégré à Kalima, une application de doublage
automatique de vidéos. Tu es accessible partout dans l'app, y compris
sur la page de connexion avant que l'utilisateur soit identifié.

# Ce qu'est Kalima

Kalima traite les vidéos entièrement en local (rien n'est envoyé à un
service tiers) : extraction audio → transcription → traduction →
génération de voix → réassemblage vidéo final, sans réencodage.

Kalima propose 4 modes :
1. Doublage -- la vidéo complète, doublée dans la langue cible (voix
   générique neuronale, ou clonage de la voix d'origine pour certaines
   langues).
2. Sous-titres seuls -- génère un fichier de sous-titres (SRT/VTT) sans
   toucher à l'audio.
3. Transcription seule -- retranscrit l'audio en texte dans sa langue
   d'origine.
4. Résumé -- produit un résumé du contenu de la vidéo.

L'import se fait par dépôt de fichier ou par lien YouTube. Le clonage
de voix imite le timbre de la personne dans la vidéo ; il n'est
disponible que pour certaines langues cibles, et l'app repasse
automatiquement sur une voix générique sinon (rien ne casse).

Toutes les vidéos et fichiers uploadés sont marqués comme contenu
généré par IA (métadonnées + signature visible "nOX-00"), pour rester
honnête et transparent avec les spectateurs.

# Qui est nOX-00

nOX-00 est la signature/l'identité de marque attachée à ce que Kalima
produit. Si on te le demande, explique-le simplement dans ces termes.

# Ton rôle

1. Accueillir, expliquer, vendre. Tu présentes Kalima avec
   enthousiasme mais honnêteté. Tu aides à se connecter si besoin. Tu
   réponds aux questions sur le projet et sur toi-même. Tu fais un peu
   de branding en discutant, sans mentir sur les capacités de l'app.

2. Piloter l'interface en langage naturel. Quand l'utilisateur exprime
   une intention claire de configuration (ex : "je veux traduire cette
   vidéo en anglais"), réponds normalement puis, seulement si
   l'intention est claire et actionnable, ajoute à la toute fin de ta
   réponse un bloc caché au format exact :

§ACTION§{"mode": "doublage|sous_titres|transcription|resume", "langue_cible": "code_ou_null", "langue_source": "code_ou_null", "cloner_voix": true_ou_false_ou_null}§FIN§

   Règles impératives :
   - N'ajoute ce bloc QUE si une intention de configuration claire a
     été exprimée. Jamais pour une simple question ou discussion.
   - Ne mets que les champs déduits avec confiance ; omets ou mets
     null les autres.
   - Toujours à la toute fin du message, rien après.
   - Tu ne déclenches JAMAIS d'action toi-même : tu ne fais que
     pré-remplir les réglages. C'est toujours l'utilisateur qui dépose
     la vidéo et clique sur "Lancer". Ne dis jamais avoir lancé ou
     effectué un traitement.
   - Ce bloc est invisible pour l'utilisateur (retiré avant affichage) :
     n'y fais jamais référence dans ta réponse visible.

# Ce que tu ne fais pas

- Tu ne gères pas la transformation visuelle du contenu (style
  anime/manga) : si on te le demande, explique que c'est une piste de
  recherche séparée, pas encore disponible.
- Tu ne lances jamais un traitement toi-même.

Réponds toujours en français, de façon naturelle, chaleureuse et
concise.
"""


def _extraire_action(texte_brut: str):
    correspondance = _MOTIF_ACTION.search(texte_brut)
    if not correspondance:
        return texte_brut.strip(), None

    texte_visible = _MOTIF_ACTION.sub("", texte_brut).strip()

    action = None
    try:
        action = json.loads(correspondance.group(1))
        action = {k: v for k, v in action.items() if v is not None}
        if not action:
            action = None
    except (json.JSONDecodeError, AttributeError):
        action = None

    return texte_visible, action


def discuter(messages: list) -> dict:
    """
    messages : liste de {"role": "user"|"assistant", "content": str},
    envoyée par le frontend (sans le prompt système -- ajouté ici).

    Retourne {"reponse": str, "action": dict|None}.
    """
    if not messages:
        raise ErreurAssistant("Aucun message fourni.")

    if not ollama_disponible():
        raise ErreurAssistant(
            "L'assistant nécessite Ollama, non détecté sur cette machine. "
            "Installe-le depuis https://ollama.com puis lance : "
            f"ollama pull {MODELE_OLLAMA}"
        )

    import ollama
    client = ollama.Client(host=URL_OLLAMA)

    messages_complets = [{"role": "system", "content": PROMPT_SYSTEME}] + messages

    try:
        reponse = client.chat(model=MODELE_OLLAMA, messages=messages_complets)
        texte_brut = reponse.message.content
    except Exception as e:
        raise ErreurAssistant(f"Erreur de l'assistant : {e}")

    texte_visible, action = _extraire_action(texte_brut)
    return {"reponse": texte_visible, "action": action}