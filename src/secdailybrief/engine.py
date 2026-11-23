"""Accès au moteur embarqué, importé tardivement et une seule fois.

Importer `veille.py` exécute son chargement de configuration : si `CONFIG_FILE` pointait
sur le mauvais fichier, l'application mourrait au démarrage avec « section inconnue ».
D'où le soin apporté ici : le chemin du périmètre est posé **avant** l'import, et l'import
n'a lieu que lorsqu'on a réellement besoin des valeurs par défaut du moteur.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from . import config as configuration
from . import paths

_module = None


def dossier() -> Path:
    """Où vit veille.py : à côté du programme en développement, dans le bundle une fois figé."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle) / "vendor"
    return paths.dossier_executable() / "vendor"


def module(dossier_donnees: Path | None = None):
    """Le module `veille`, importé au premier appel."""
    global _module
    if _module is None:
        if dossier_donnees is not None:
            os.environ["CONFIG_FILE"] = str(configuration.chemin_perimetre(dossier_donnees))
        sys.path.insert(0, str(dossier()))
        import veille  # noqa: PLC0415 - import volontairement tardif

        _module = veille
    return _module


def stack_par_defaut(dossier_donnees: Path | None = None) -> dict[str, list[str]]:
    """La stack livrée avec le moteur — celle de l'auteur, proposée comme exemple."""
    return {nom: list(mots) for nom, mots in module(dossier_donnees).STACK_PRODUCTS.items()}
