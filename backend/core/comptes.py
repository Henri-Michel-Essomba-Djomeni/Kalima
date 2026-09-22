"""
Comptes utilisateurs pour Kalima.

Remplace l'ancien système à identifiant unique partagé (admin/mot de
passe global) par de vrais comptes : email + mot de passe, avec
vérification d'email obligatoire avant de pouvoir se connecter.

Persistance SQLite (stdlib, zéro dépendance externe), même approche
que job_manager.py.

Vérification d'email : on ne peut pas prouver qu'une adresse "existe"
autrement qu'en lui envoyant réellement un message que seul son
propriétaire peut recevoir. C'est ce que fait ce module : un jeton
unique est envoyé par email à l'inscription, et le compte reste
"non vérifié" (donc bloqué à la connexion) tant que le lien n'a pas
été cliqué. Si l'adresse n'existe pas, l'email n'arrivera jamais et
le compte ne sera jamais activé -- c'est la vérification.
"""

import hashlib
import os
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, date

DOSSIER_DB = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "jobs",  # même dossier que jobs.db, pas besoin d'un dossier séparé
)
os.makedirs(DOSSIER_DB, exist_ok=True)
CHEMIN_DB = os.path.join(DOSSIER_DB, "comptes.db")

DUREE_SESSION = timedelta(days=30)

_verrou = threading.Lock()


class ErreurCompte(Exception):
    pass


def _init_db():
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS utilisateurs ("
            "id TEXT PRIMARY KEY, "
            "email TEXT UNIQUE NOT NULL, "
            "mot_de_passe_hash TEXT NOT NULL, "
            "sel TEXT NOT NULL, "
            "email_verifie INTEGER DEFAULT 0, "
            "jeton_verification TEXT, "
            "cree_le TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS sessions ("
            "jeton TEXT PRIMARY KEY, "
            "utilisateur_id TEXT NOT NULL, "
            "expire_le TEXT NOT NULL)"
        )
        conn.execute(
            "CREATE TABLE IF NOT EXISTS usage_quotidien ("
            "utilisateur_id TEXT NOT NULL, "
            "date TEXT NOT NULL, "
            "nombre_jobs INTEGER DEFAULT 0, "
            "PRIMARY KEY (utilisateur_id, date))"
        )


_init_db()


def _hacher_mot_de_passe(mot_de_passe: str, sel: bytes) -> str:
    return hashlib.pbkdf2_hmac("sha256", mot_de_passe.encode(), sel, 100_000).hex()


# ---------------------------------------------------------------------------
# Inscription et vérification d'email
# ---------------------------------------------------------------------------

def creer_utilisateur(email: str, mot_de_passe: str) -> tuple[str, str]:
    """
    Crée un compte non vérifié. Retourne (utilisateur_id, jeton_verification)
    -- le jeton est à envoyer par email, jamais affiché à l'utilisateur.
    """
    email = email.strip().lower()

    if "@" not in email or "." not in email.split("@")[-1]:
        raise ErreurCompte("Adresse email invalide.")

    if len(mot_de_passe) < 8:
        raise ErreurCompte("Le mot de passe doit faire au moins 8 caractères.")

    utilisateur_id = secrets.token_hex(16)
    sel = secrets.token_bytes(16)
    hash_mdp = _hacher_mot_de_passe(mot_de_passe, sel)
    jeton = secrets.token_urlsafe(32)
    maintenant = datetime.utcnow().isoformat()

    try:
        with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
            conn.execute(
                "INSERT INTO utilisateurs "
                "(id, email, mot_de_passe_hash, sel, email_verifie, jeton_verification, cree_le) "
                "VALUES (?, ?, ?, ?, 0, ?, ?)",
                (utilisateur_id, email, hash_mdp, sel.hex(), jeton, maintenant),
            )
    except sqlite3.IntegrityError:
        raise ErreurCompte("Un compte existe déjà avec cet email.")

    return utilisateur_id, jeton


def verifier_email(jeton: str) -> bool:
    """Active le compte correspondant au jeton. Retourne True si trouvé."""
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        curseur = conn.execute(
            "UPDATE utilisateurs SET email_verifie = 1, jeton_verification = NULL "
            "WHERE jeton_verification = ?",
            (jeton,),
        )
        return curseur.rowcount > 0


# ---------------------------------------------------------------------------
# Connexion et sessions
# ---------------------------------------------------------------------------

def authentifier(email: str, mot_de_passe: str) -> str:
    """Retourne l'utilisateur_id si les identifiants sont valides et le compte vérifié."""
    email = email.strip().lower()

    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute(
            "SELECT * FROM utilisateurs WHERE email = ?", (email,)
        ).fetchone()

    if ligne is None:
        raise ErreurCompte("Identifiants incorrects.")

    hash_attendu = _hacher_mot_de_passe(mot_de_passe, bytes.fromhex(ligne["sel"]))
    if not secrets.compare_digest(hash_attendu, ligne["mot_de_passe_hash"]):
        raise ErreurCompte("Identifiants incorrects.")

    if not ligne["email_verifie"]:
        raise ErreurCompte("Compte non vérifié -- clique sur le lien reçu par email.")

    return ligne["id"]


def creer_session(utilisateur_id: str) -> str:
    jeton = secrets.token_hex(32)
    expire_le = (datetime.utcnow() + DUREE_SESSION).isoformat()
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute(
            "INSERT INTO sessions (jeton, utilisateur_id, expire_le) VALUES (?, ?, ?)",
            (jeton, utilisateur_id, expire_le),
        )
    return jeton


def utilisateur_depuis_session(jeton: str) -> str | None:
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute(
            "SELECT * FROM sessions WHERE jeton = ?", (jeton,)
        ).fetchone()

    if ligne is None:
        return None
    if datetime.fromisoformat(ligne["expire_le"]) < datetime.utcnow():
        return None
    return ligne["utilisateur_id"]


def supprimer_session(jeton: str) -> None:
    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.execute("DELETE FROM sessions WHERE jeton = ?", (jeton,))


# ---------------------------------------------------------------------------
# Quota d'usage quotidien
# ---------------------------------------------------------------------------

LIMITE_JOBS_PAR_JOUR = int(os.environ.get("KALIMA_LIMITE_JOBS_JOUR", "5"))


def verifier_et_incrementer_quota(utilisateur_id: str, limite: int = LIMITE_JOBS_PAR_JOUR) -> None:
    """Lève ErreurCompte si le quota du jour est atteint, sinon incrémente."""
    aujourdhui = date.today().isoformat()

    with _verrou, sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute(
            "SELECT nombre_jobs FROM usage_quotidien WHERE utilisateur_id = ? AND date = ?",
            (utilisateur_id, aujourdhui),
        ).fetchone()

        nombre_actuel = ligne["nombre_jobs"] if ligne else 0

        if nombre_actuel >= limite:
            raise ErreurCompte(
                f"Limite quotidienne atteinte ({limite} traitements par jour). Réessaie demain."
            )

        if ligne:
            conn.execute(
                "UPDATE usage_quotidien SET nombre_jobs = nombre_jobs + 1 "
                "WHERE utilisateur_id = ? AND date = ?",
                (utilisateur_id, aujourdhui),
            )
        else:
            conn.execute(
                "INSERT INTO usage_quotidien (utilisateur_id, date, nombre_jobs) VALUES (?, ?, 1)",
                (utilisateur_id, aujourdhui),
            )


def obtenir_email(utilisateur_id: str) -> str | None:
    with sqlite3.connect(CHEMIN_DB) as conn:
        conn.row_factory = sqlite3.Row
        ligne = conn.execute(
            "SELECT email FROM utilisateurs WHERE id = ?", (utilisateur_id,)
        ).fetchone()
    return ligne["email"] if ligne else None