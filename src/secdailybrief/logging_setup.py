"""Journal de l'application : horodaté, en UTF-8, avec rotation.

Le format est décidé ici et nulle part ailleurs : le moteur écrit ses propres messages
sans horodatage (ils sont préfixés par GitHub Actions en production), donc c'est le
lanceur qui date les lignes qu'il capture. Sans ça, le filtre par date du panneau
n'aurait rien sur quoi s'appuyer.
"""
from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path

FORMAT = "%(asctime)s %(levelname)-7s %(message)s"
DATE = "%Y-%m-%d %H:%M:%S"
TAILLE_MAX = 2 * 1024 * 1024   # 2 Mo
SAUVEGARDES = 5                # ~10 Mo d'historique, largement de quoi tenir un mois

_NIVEAU = re.compile(r"^(INFO|WARNING|WARN|ERROR|CRITICAL|DEBUG)\b")


def journaliser(chemin: Path, niveau: int = logging.INFO) -> logging.Logger:
    """Configure le journal applicatif et renvoie son logger."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("secdailybrief")
    logger.setLevel(niveau)
    # clear() sans close() laissait un descripteur ouvert a chaque appel : le journal etait
    # rouvert des dizaines de fois dans une session.
    for gestionnaire in list(logger.handlers):
        try:
            gestionnaire.close()
        except Exception:       # noqa: BLE001 - un handler deja ferme n'est pas une erreur
            pass
    logger.handlers.clear()
    gestionnaire = RotatingFileHandler(chemin, maxBytes=TAILLE_MAX,
                                       backupCount=SAUVEGARDES, encoding="utf-8")
    gestionnaire.setFormatter(logging.Formatter(FORMAT, DATE))
    logger.addHandler(gestionnaire)
    logger.propagate = False
    return logger


def ligne_horodatee(ligne: str) -> str:
    """Relit une ligne écrite par le moteur et lui donne un horodatage.

    « INFO  Report size: 129.3 KB » devient « 2026-11-23 17:44:00 INFO     Report size… ».
    Une ligne sans niveau connu est conservée telle quelle, précédée de l'heure : on ne
    réécrit pas la sortie de quelqu'un d'autre, on la date.
    """
    ligne = ligne.rstrip("\r\n")
    correspondance = _NIVEAU.match(ligne)
    if correspondance:
        niveau, reste = correspondance.group(1), ligne[correspondance.end():].lstrip()
        return f"{_maintenant()} {niveau:<7} {reste}"
    return f"{_maintenant()} {'':<7} {ligne}"


def _maintenant() -> str:
    from datetime import datetime
    return datetime.now().strftime(DATE)
