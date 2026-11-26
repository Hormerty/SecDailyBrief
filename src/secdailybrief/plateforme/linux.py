"""Implémentation Linux : trousseau du bureau, verrou de fichier, XDG.

Le chiffrement n'a pas d'équivalent exact de DPAPI. Trois cas, du meilleur au plus modeste :

* **Secret Service** (`secret-tool`, paquet `libsecret-tools`) : le secret est rangé dans le
  trousseau de la session, déverrouillé avec la connexion. C'est le bon cas.
* **Fichier en 0600** : sans trousseau — machine sans bureau, conteneur, serveur — le secret
  est écrit lisible par le seul propriétaire. C'est plus faible que DPAPI, et le diagnostic
  doit le dire plutôt que de laisser croire à l'équivalent.
* **Aucun des deux** : le fichier est écrit quand même, avec les mêmes droits, mais un
  avertissement est journalisé.

Le format de fichier reste base64 du secret, comme sous Windows : un même fichier de données
reste lisible des deux côtés, à ceci près que le contenu n'est plus chiffré par le système.
"""
from __future__ import annotations

import base64
import contextlib
import fcntl
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

NOM = "trousseau du bureau (Secret Service)"
ATTRIBUTS = ("service", "SecDailyBrief")

#: Vrai si `secret-tool` est présent : le diagnostic s'en sert pour être honnête.
TROUSSEAU_DISPONIBLE = shutil.which("secret-tool") is not None


def _secret_tool(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["secret-tool", *arguments], capture_output=True, check=False)


def _cle() -> list[str]:
    utilisateur = os.environ.get("USER") or os.environ.get("LOGNAME") or "utilisateur"
    attributs: list[str] = []
    for etiquette, valeur in (ATTRIBUTS, ("account", utilisateur)):
        attributs.extend([etiquette, valeur])
    return attributs


def chiffrer(texte: str) -> bytes:
    """Range le secret dans le trousseau s'il existe, sinon le rend tel quel.

    Le fichier appelant fait `base64(chiffrer(...))` : sans trousseau, il contient donc du
    base64 de clair, protégé par les droits du fichier (0600) — ce que le diagnostic annonce.
    """
    if TROUSSEAU_DISPONIBLE:
        resultat = _secret_tool("store", "--label=SecDailyBrief", *_cle(), value=texte)
        if resultat.returncode == 0:
            # Le trousseau a le secret ; le fichier ne garde qu'un marqueur.
            return b"secret-service"
    return texte.encode("utf-8")


def dechiffrer(chiffre: bytes) -> str:
    if chiffre == b"secret-service" or TROUSSEAU_DISPONIBLE:
        resultat = _secret_tool("lookup", *_cle())
        if resultat.returncode == 0 and resultat.stdout:
            return resultat.stdout.decode("utf-8")
        if chiffre == b"secret-service":
            raise OSError("secret absent du trousseau (session verrouillee ?)")
    return chiffre.decode("utf-8")


@contextlib.contextmanager
def verrou_instance(nom: str = "SecDailyBrief"):
    """Verrou de fichier : `flock` le relâche à la mort du processus, même tué.

    Le nom Windows (`Local\\SecDailyBrief`) est réduit à un nom de fichier portable, et placé
    dans le dossier temporaire de l'utilisateur.
    """
    propre = nom.replace("\\", "_").replace("/", "_").strip("_") or "SecDailyBrief"
    chemin = Path(tempfile.gettempdir()) / f".{propre}.lock"
    descripteur = os.open(chemin, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(descripteur, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(descripteur, fcntl.LOCK_UN)
    finally:
        os.close(descripteur)


def dossier_donnees() -> Path | None:
    """XDG : `~/.local/share/SecDailyBrief`, ou `$XDG_DATA_HOME` s'il est défini."""
    base = os.environ.get("XDG_DATA_HOME")
    racine = Path(base) if base else Path.home() / ".local" / "share"
    return racine / "SecDailyBrief"


def dans_wsl() -> bool:
    """Vrai si l'on tourne dans WSL : la distribution s'arrete quand rien ne tourne."""
    try:
        return "microsoft" in Path("/proc/version").read_text(encoding="utf-8").lower()
    except OSError:
        return False


def linger_actif() -> bool:
    """Vrai si le gestionnaire systemd de l'utilisateur survit a la fermeture de session."""
    utilisateur = os.environ.get("USER") or os.environ.get("LOGNAME") or ""
    if not utilisateur:
        return False
    resultat = subprocess.run(["loginctl", "show-user", utilisateur, "-p", "Linger"],
                              capture_output=True, text=True, check=False)
    return resultat.stdout.strip().lower() == "linger=yes"
