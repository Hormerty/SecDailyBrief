"""Historique des exécutions, borné et lisible.

Le journal dit tout, ligne par ligne, mais personne ne l'ouvre pour savoir si le rapport est
parti hier. Ce fichier garde une ligne par exécution — date, mode, statut, durée — et
n'enregistre rien d'autre : c'est un résumé, pas une seconde source de vérité.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from . import paths

NOM = "historique.json"
MAX_ENTREES = 60
JOURS_AFFICHES = 7


def chemin() -> Path:
    return paths.chemin_etat(NOM)


def charger() -> list[dict]:
    """Les entrées enregistrées, ou une liste vide si le fichier manque ou est abîmé."""
    try:
        donnees = json.loads(chemin().read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return []
    if not isinstance(donnees, list):
        return []
    return [entree for entree in donnees if isinstance(entree, dict)]


def enregistrer(statut: str, duree: float, mode: str,
                maintenant: datetime | None = None) -> None:
    """Ajoute une exécution. Écriture atomique : jamais de fichier à moitié écrit."""
    moment = maintenant or datetime.now()
    entrees = charger()
    entrees.append({"date": moment.isoformat(timespec="seconds"), "statut": statut,
                    "duree": round(duree, 1), "mode": mode})
    entrees = entrees[-MAX_ENTREES:]

    destination = chemin()
    destination.parent.mkdir(parents=True, exist_ok=True)
    provisoire = destination.with_suffix(".tmp")
    provisoire.write_text(json.dumps(entrees, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    os.replace(provisoire, destination)


def recentes(jours: int = JOURS_AFFICHES, maintenant: datetime | None = None) -> list[dict]:
    """Les entrées des derniers jours, de la plus récente à la plus ancienne."""
    moment = maintenant or datetime.now()
    limite = moment - timedelta(days=jours)
    retenues: list[dict] = []
    for entree in charger():
        try:
            date = datetime.fromisoformat(str(entree["date"]))
        except (KeyError, TypeError, ValueError):
            continue
        if date >= limite:
            retenues.append(entree)
    return list(reversed(retenues))
