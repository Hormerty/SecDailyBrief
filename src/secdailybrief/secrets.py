"""Chiffrement local des secrets : mot de passe SMTP, webhooks, jetons d'API.

Le stockage réel dépend du système — DPAPI sous Windows, trousseau du bureau sous Linux — et
c'est `plateforme` qui tranche. Ce module garde l'API historique et le format de fichier :
du base64, pour rester inspectable sans être lisible d'un coup d'œil.
"""
from __future__ import annotations

import base64
import os
import json
from pathlib import Path

from . import plateforme


def proteger(texte: str) -> bytes:
    return plateforme.chiffrer(texte)


def deproteger(chiffre: bytes) -> str:
    return plateforme.dechiffrer(chiffre)


def enregistrer(chemin: Path, mot_de_passe: str) -> None:
    """Écrit le secret chiffré, en base64 pour rester inspectable sans être lisible."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    donnees = base64.b64encode(proteger(mot_de_passe))
    # Sans trousseau, le fichier *est* la protection. On le crée directement en 0600 : écrire
    # puis chmod laissait, sous umask 022, une fenêtre pendant laquelle le secret était lisible
    # par tous.
    try:
        descripteur = os.open(chemin, os.O_CREAT | os.O_WRONLY | os.O_TRUNC, 0o600)
    except OSError:            # noqa: BLE001 - Windows ignore les modes POSIX
        chemin.write_bytes(donnees)
    else:
        with os.fdopen(descripteur, "wb") as fichier:
            fichier.write(donnees)
    try:
        chemin.chmod(0o600)    # un fichier qui existait déjà garde son ancien mode
    except OSError:            # noqa: BLE001 - Windows ignore les modes POSIX
        pass


def charger(chemin: Path) -> str | None:
    """Relit le secret, ou None s'il n'y en a pas, ou s'il est illisible.

    Un fichier tronque, copie d'une autre machine ou ecrit par un autre compte leve ici :
    binascii.Error sur le base64, UnicodeDecodeError sur le clair, OSError quand DPAPI refuse
    de dechiffrer. Non rattrape, cela empechait l'application de demarrer, sans aucun moyen de
    ressaisir le mot de passe depuis l'interface.
    """
    if not chemin.exists():
        return None
    # On leve, volontairement : un blob modifie doit se voir, pas se confondre avec « pas de
    # mot de passe ». Ce sont les appelants qui rattrapent, pour que l'application s'ouvre au
    # lieu de mourir sur un fichier abime.
    return deproteger(base64.b64decode(chemin.read_bytes()))


def effacer(chemin: Path) -> None:
    chemin.unlink(missing_ok=True)


def enregistrer_jetons(chemin: Path, jetons: dict[str, str]) -> None:
    """Chiffre tous les secrets ensemble : un mot de passe SMTP, des clés d'API, un webhook.

    Un seul blob, donc un seul fichier à sauvegarder, à déplacer ou à effacer — et aucune clé
    en clair dans le JSON de configuration, qui reste lisible.
    """
    enregistrer(chemin, json.dumps(jetons, ensure_ascii=False))


def charger_jetons(chemin: Path) -> dict[str, str]:
    """Relit le dictionnaire de secrets ; {} s'il n'y en a pas encore."""
    texte = charger(chemin)
    if not texte:
        return {}
    try:
        donnees = json.loads(texte)
    except json.JSONDecodeError:
        return {}
    return {cle: valeur for cle, valeur in donnees.items() if isinstance(valeur, str)}
