"""
Envoi de l'email de vérification à l'inscription.

Utilise smtplib (stdlib) -- aucune dépendance externe, aucun service
payant. Il faut un compte SMTP pour envoyer réellement les emails
(Gmail avec un "mot de passe d'application", ou tout autre
fournisseur SMTP -- Brevo/Sendinblue a un plan gratuit adapté à ce
volume si tu n'as pas déjà un email pro).

Configuration via variables d'environnement :
  KALIMA_SMTP_HOTE          ex: smtp.gmail.com
  KALIMA_SMTP_PORT          ex: 587
  KALIMA_SMTP_UTILISATEUR   ton adresse d'envoi
  KALIMA_SMTP_MOT_DE_PASSE  mot de passe d'application (PAS ton mot de passe normal)
  KALIMA_SMTP_EXPEDITEUR    adresse affichée comme expéditeur (souvent la même que UTILISATEUR)
  KALIMA_URL_BASE           ex: https://kalima.tondomaine.com (ou http://localhost:8000 en dev)

Si KALIMA_SMTP_HOTE n'est pas défini, l'email n'est pas envoyé : le
lien de vérification est juste affiché dans les logs du serveur.
Pratique en développement, mais À NE PAS garder une fois en ligne --
sans ça personne ne peut vérifier son compte.
"""

import os
import smtplib
from email.mime.text import MIMEText

SMTP_HOTE = os.environ.get("KALIMA_SMTP_HOTE")
SMTP_PORT = int(os.environ.get("KALIMA_SMTP_PORT", "587"))
SMTP_UTILISATEUR = os.environ.get("KALIMA_SMTP_UTILISATEUR")
SMTP_MOT_DE_PASSE = os.environ.get("KALIMA_SMTP_MOT_DE_PASSE")
SMTP_EXPEDITEUR = os.environ.get("KALIMA_SMTP_EXPEDITEUR", SMTP_UTILISATEUR)
URL_BASE = os.environ.get("KALIMA_URL_BASE", "http://localhost:8000")


def envoyer_email_verification(destinataire: str, jeton: str) -> None:
    lien = f"{URL_BASE}/verifier-email?jeton={jeton}"

    if not SMTP_HOTE:
        print(f"[Kalima] SMTP non configuré -- lien de vérification pour {destinataire} : {lien}")
        return

    message = MIMEText(
        f"Bienvenue sur Kalima !\n\n"
        f"Clique sur ce lien pour activer ton compte :\n{lien}\n\n"
        f"Si tu n'es pas à l'origine de cette inscription, ignore cet email.\n\n"
        f"-- nOX-00"
    )
    message["Subject"] = "Vérifie ton compte Kalima"
    message["From"] = SMTP_EXPEDITEUR
    message["To"] = destinataire

    with smtplib.SMTP(SMTP_HOTE, SMTP_PORT) as serveur:
        serveur.starttls()
        serveur.login(SMTP_UTILISATEUR, SMTP_MOT_DE_PASSE)
        serveur.sendmail(SMTP_EXPEDITEUR, [destinataire], message.as_string())
