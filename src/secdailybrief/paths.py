"""Où vivent les fichiers de l'application.

Deux modes, une seule règle : rien n'est écrit dans le dossier du programme, sauf si
l'utilisateur a explicitement choisi le mode portable (un fichier `portable.flag` posé à
côté de l'exécutable). Dans ce cas les données voyagent avec le programme, sur la clé USB
ou le disque, et non dans le profil Windows.

L'ordre de résolution est volontairement explicite, et l'environnement passe en premier :
c'est ce qui permet aux tests de travailler dans un dossier temporaire sans jamais toucher
au profil réel.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

NOM_APPLICATION = "SecDailyBrief"
VARIABLE_DONNEES = "SECDailyBrief_DATA"
MARQUEUR_PORTABLE = "portable.flag"


def dossier_executable() -> Path:
    """Dossier de l'exécutable (PyInstaller) ou racine du dépôt en développement."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent.parent


def dossier_ressources() -> Path:
    """Dossier des ressources embarquées (icône, logo).

    Dans un binaire figé, elles sont décompressées hors du dossier de l'exécutable :
    `dossier_executable()` ne les voit pas.
    """
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS", dossier_executable())) / "assets"
    return Path(__file__).resolve().parent.parent.parent / "assets"


def est_portable() -> bool:
    return (dossier_executable() / MARQUEUR_PORTABLE).exists()


def dossier_donnees() -> Path:
    """Dossier de travail : imposé par l'environnement, portable, ou %APPDATA%."""
    impose = os.environ.get(VARIABLE_DONNEES)
    if impose:
        return Path(impose).expanduser()
    if est_portable():
        return dossier_executable() / "data"
    appdata = os.environ.get("APPDATA")
    base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    return base / NOM_APPLICATION


def s_assurer_dossier() -> Path:
    """Crée le dossier de données au besoin et vérifie qu'on peut y écrire.

    Le test d'écriture n'est pas décoratif : en mode portable lancé depuis un support en
    lecture seule, on veut un message clair tout de suite, pas une erreur au premier
    enregistrement de configuration.
    """
    dossier = dossier_donnees()
    dossier.mkdir(parents=True, exist_ok=True)
    sonde = dossier / ".ecriture"
    try:
        sonde.write_text("ok", encoding="utf-8")
    except OSError as exc:
        raise OSError(f"dossier de données non inscriptible : {dossier}") from exc
    finally:
        sonde.unlink(missing_ok=True)
    return dossier


def chemin_config() -> Path:
    return dossier_donnees() / "config.json"


def chemin_secret() -> Path:
    return dossier_donnees() / "secret.dpapi"


def chemin_journal() -> Path:
    return dossier_donnees() / "journal.log"


def chemin_etat(nom: str) -> Path:
    """Fichiers d'état du moteur : seen.json, stats.db, caches…"""
    return dossier_donnees() / nom
