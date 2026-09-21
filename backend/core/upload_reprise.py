"""
Upload robuste avec reprise sur coupure réseau.

Le fichier est envoyé par petits morceaux (chunks) depuis le navigateur.
Chaque morceau est identifié par une "empreinte" du fichier (nom + taille
+ date de modification -- même logique que la mémoire de transcription)
et un décalage (offset) en octets. Le serveur écrit les morceaux dans
l'ordre reçu et sait à tout moment combien d'octets il a déjà reçus pour
une empreinte donnée : en cas de coupure réseau, on reprend exactement
où on s'est arrêté plutôt que de tout renvoyer.
"""

import os
import json

DOSSIER_REPRISE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "uploads", "en_cours"
)
os.makedirs(DOSSIER_REPRISE, exist_ok=True)


def _chemins(empreinte: str):
    dossier = os.path.join(DOSSIER_REPRISE, empreinte)
    return dossier, os.path.join(dossier, "donnees.part"), os.path.join(dossier, "meta.json")


def initialiser_upload(empreinte: str, nom_fichier: str, taille_totale: int) -> int:
    """Crée (ou retrouve) une session d'upload. Retourne le nombre d'octets déjà reçus."""
    dossier, chemin_donnees, chemin_meta = _chemins(empreinte)
    os.makedirs(dossier, exist_ok=True)

    if not os.path.exists(chemin_meta):
        with open(chemin_meta, "w") as f:
            json.dump({"nom_fichier": nom_fichier, "taille_totale": taille_totale}, f)

    if os.path.exists(chemin_donnees):
        return os.path.getsize(chemin_donnees)
    return 0


def ecrire_morceau(empreinte: str, offset: int, morceau: bytes) -> int:
    """
    Écrit un morceau à la position attendue.
    Retourne le nombre total d'octets reçus après écriture.
    Si le morceau ne correspond pas à ce qu'on attend (doublon, ou trou
    suite à une coupure), on l'ignore et on renvoie juste l'état réel
    pour que le client se resynchronise dessus.
    """
    dossier, chemin_donnees, chemin_meta = _chemins(empreinte)
    if not os.path.exists(chemin_meta):
        raise ValueError("Upload non initialisé pour cette empreinte.")

    taille_actuelle = os.path.getsize(chemin_donnees) if os.path.exists(chemin_donnees) else 0

    if offset != taille_actuelle:
        return taille_actuelle

    with open(chemin_donnees, "ab") as f:
        f.write(morceau)

    return taille_actuelle + len(morceau)


def upload_est_complet(empreinte: str) -> bool:
    dossier, chemin_donnees, chemin_meta = _chemins(empreinte)
    if not (os.path.exists(chemin_donnees) and os.path.exists(chemin_meta)):
        return False
    with open(chemin_meta) as f:
        meta = json.load(f)
    return os.path.getsize(chemin_donnees) >= meta["taille_totale"]


def finaliser_upload(empreinte: str, dossier_destination: str, prefixe: str) -> str:
    """
    Déplace le fichier complet vers son emplacement final (le dossier
    uploads/ habituel de Kalima) et nettoie la session de reprise.
    Retourne le chemin final du fichier.
    """
    dossier, chemin_donnees, chemin_meta = _chemins(empreinte)

    if not upload_est_complet(empreinte):
        raise ValueError("Upload incomplet, impossible de finaliser.")

    with open(chemin_meta) as f:
        meta = json.load(f)

    chemin_final = os.path.join(dossier_destination, f"{prefixe}_{meta['nom_fichier']}")
    os.replace(chemin_donnees, chemin_final)
    os.remove(chemin_meta)
    try:
        os.rmdir(dossier)
    except OSError:
        pass

    return chemin_final
