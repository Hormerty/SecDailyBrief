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
#: Sept jours à neuf passages quotidiens (le rapport et huit alertes) font 63 entrées : la borne
#: précédente, 60, en tronquait une, donc la fenêtre de sept jours affichait six jours et demi.
MAX_ENTREES = 200
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
                maintenant: datetime | None = None, origine: str = "") -> None:
    """Ajoute une exécution. Écriture atomique : jamais de fichier à moitié écrit.

    Deux processus peuvent lancer une exécution dans la même seconde (le planificateur et
    l'interface, par exemple). Sans fusion, l'historique affichait alors deux lignes au même
    horodatage et de statuts opposés, ce qui était illisible. Une ligne identique est donc
    fusionnée avec la plus grave, et l'origine dit qui a lancé quoi.
    """
    moment = maintenant or datetime.now()
    entrees = charger()
    horodatage = moment.isoformat(timespec="seconds")
    entree = {"date": horodatage, "statut": statut, "duree": round(duree, 1), "mode": mode,
              "origine": origine}
    precedente = entrees[-1] if entrees else None
    if (precedente and precedente.get("date") == horodatage
            and precedente.get("mode") == mode):
        # Même seconde, même mode : on garde le statut le plus grave et la durée la plus longue.
        if statut != "ok" or not precedente.get("statut"):
            precedente["statut"] = statut
            precedente["duree"] = max(float(precedente.get("duree") or 0), round(duree, 1))
        if origine:
            precedente["origine"] = origine
    else:
        entrees.append(entree)
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
