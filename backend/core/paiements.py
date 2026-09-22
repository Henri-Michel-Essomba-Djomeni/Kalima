"""
Paiement pour Kalima, via CamerPay (passerelle camerounaise -- Orange
Money, MTN MoMo, cartes, PayPal). Documentation : https://camerpay.biz/docs

Deux façons de débloquer un traitement qui dépasse le gratuit
(quota quotidien atteint OU fichier au-dessus du seuil de taille) :

  - "pro"    : abonnement mensuel, retire quota ET seuil de taille pendant 30 jours.
  - "credit" : paiement unique, débloque UN SEUL traitement supplémentaire.

Persistance SQLite (même base que comptes.py -- comptes.db).
"""

import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta

import requests

from .comptes import CHEMIN_DB, _verrou

CAMERPAY_TOKEN = os.environ.get("KALIMA_CAMERPAY_TOKEN")
CAMERPAY_CALLBACK_SECRET = os.environ.get("KALIMA_CAMERPAY_CALLBACK_SECRET")
CAMERPAY_BASE_URL = os.environ.get("KALIMA_CAMERPAY_BASE_URL", "https://camerpay.biz/api")
URL_BASE = os.environ.get("KALIMA_URL_BASE", "http://localhost:8000")

PRIX_PRO_XAF = int(os.environ.get("KALIMA_PRIX_PRO_XAF", "5000"))
PRIX_CREDIT_XAF = int(os.environ.get("KALIMA_PRIX_CREDIT_XAF", "500"))
SEUIL_TAILLE_GRATUITE_MO = int(os.environ.get("KALIMA_SEUIL_TAILLE_GRATUITE_MO", "300"))
SEUIL_TAILLE_GRATUITE_OCTETS = SEUIL_TAILLE_GRATUITE_MO * 1024 * 1024

DUREE_PRO = timedelta(days=30)


class ErreurPaiement(Exception):
    pass


def _init_db():
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS abonnements ("
            "utilisateur_id TEXT PRIMARY KEY, "
            "expire_le TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS credits_ponctuels ("
            "utilisateur_id TEXT PRIMARY KEY, "
            "nombre INTEGER NOT NULL DEFAULT 0)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS transactions_paiement ("
            "uuid TEXT PRIMARY KEY, "
            "utilisateur_id TEXT NOT NULL, "
            "type TEXT NOT NULL, "  # 'pro' ou 'credit'
            "montant REAL NOT NULL, "
            "statut TEXT NOT NULL DEFAULT 'pending', "
            "cree_le TEXT NOT NULL)"
        )


_init_db()


# ---------------------------------------------------------------------------
# État d'un utilisateur
# ---------------------------------------------------------------------------

def est_pro(utilisateur_id: str) -> bool:
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute(
            "SELECT expire_le FROM abonnements WHERE utilisateur_id = ?",
            (utilisateur_id,),
        ).fetchone()
    return bool(ligne) and datetime.fromisoformat(ligne["expire_le"]) > datetime.utcnow()


def nombre_credits(utilisateur_id: str) -> int:
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute(
            "SELECT nombre FROM credits_ponctuels WHERE utilisateur_id = ?",
            (utilisateur_id,),
        ).fetchone()
    return ligne["nombre"] if ligne else 0


def consommer_credit(utilisateur_id: str) -> bool:
    """Retire 1 crédit si dispo. Retourne True si ça a marché."""
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute(
            "SELECT nombre FROM credits_ponctuels WHERE utilisateur_id = ?",
            (utilisateur_id,),
        ).fetchone()
        if not ligne or ligne["nombre"] <= 0:
            return False
        conn.execute(
            "UPDATE credits_ponctuels SET nombre = nombre - 1 WHERE utilisateur_id = ?",
            (utilisateur_id,),
        )
        return True


def _activer_pro(utilisateur_id: str) -> None:
    expire_le = (datetime.utcnow() + DUREE_PRO).isoformat()
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "INSERT INTO abonnements (utilisateur_id, expire_le) VALUES (?, ?) "
            "ON CONFLICT(utilisateur_id) DO UPDATE SET expire_le = ?",
            (utilisateur_id, expire_le, expire_le),
        )


def _ajouter_credit(utilisateur_id: str) -> None:
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "INSERT INTO credits_ponctuels (utilisateur_id, nombre) VALUES (?, 1) "
            "ON CONFLICT(utilisateur_id) DO UPDATE SET nombre = nombre + 1",
            (utilisateur_id,),
        )


# ---------------------------------------------------------------------------
# Initiation d'un paiement
# ---------------------------------------------------------------------------

def initier_paiement(utilisateur_id: str, email: str, type_achat: str) -> str:
    """
    type_achat : 'pro' ou 'credit'.
    Retourne l'URL de paiement CamerPay vers laquelle rediriger l'utilisateur.
    """
    if type_achat not in ("pro", "credit"):
        raise ErreurPaiement("Type d'achat invalide.")

    if not CAMERPAY_TOKEN:
        raise ErreurPaiement("Paiement non configuré (CamerPay non renseigné).")

    montant = PRIX_PRO_XAF if type_achat == "pro" else PRIX_CREDIT_XAF
    invoice_id = f"{type_achat}_{utilisateur_id}_{secrets.token_hex(6)}"

    reponse = requests.post(
        f"{CAMERPAY_BASE_URL}/payment/initiate",
        headers={"Authorization": f"Bearer {CAMERPAY_TOKEN}"},
        json={
            "amount": montant,
            "currency": "XAF",
            "customer_email": email,
            "merchant_invoice_id": invoice_id,
            "merchant_callback_url": f"{URL_BASE}/api/paiement/webhook",
            "merchant_return_url": f"{URL_BASE}/?paiement=retour",
            "source": "kalima",
        },
        timeout=15,
    )

    donnees = reponse.json()
    if not donnees.get("success"):
        raise ErreurPaiement(donnees.get("message", "Échec de l'initiation du paiement."))

    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "INSERT INTO transactions_paiement (uuid, utilisateur_id, type, montant, statut, cree_le) "
            "VALUES (?, ?, ?, ?, 'pending', ?)",
            (donnees["transaction_uuid"], utilisateur_id, type_achat, montant, datetime.utcnow().isoformat()),
        )

    return donnees["pay_url"]


# ---------------------------------------------------------------------------
# Webhook entrant
# ---------------------------------------------------------------------------

def verifier_signature_webhook(uuid: str, invoice_id: str, statut: str, montant: str, signature: str) -> bool:
    if not CAMERPAY_CALLBACK_SECRET:
        return False
    donnees = f"{uuid}|{invoice_id}|{statut}|{montant}"
    attendu = hmac.new(
        CAMERPAY_CALLBACK_SECRET.encode(), donnees.encode(), hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(attendu, signature)


def traiter_webhook(uuid: str, statut: str) -> None:
    """Applique l'effet du paiement (pro ou crédit) une fois confirmé -- idempotent."""
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute(
            "SELECT * FROM transactions_paiement WHERE uuid = ?", (uuid,)
        ).fetchone()

    if not ligne:
        raise ErreurPaiement("Transaction inconnue.")

    if ligne["statut"] == "completed":
        return  # déjà traité, on ignore (webhook rejoué)

    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "UPDATE transactions_paiement SET statut = ? WHERE uuid = ?", (statut, uuid)
        )

    if statut == "completed":
        if ligne["type"] == "pro":
            _activer_pro(ligne["utilisateur_id"])
        else:
            _ajouter_credit(ligne["utilisateur_id"])
