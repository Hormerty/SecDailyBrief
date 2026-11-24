"""Sait s'il existe une version plus récente publiée sur GitHub.

Aucun serveur à nous : la dernière release est lue par l'API publique de GitHub. Le jour où
le dépôt n'existe pas encore, ou quand la machine est hors ligne, la fonction renvoie None
et l'interface n'affiche rien — un bandeau de mise à jour ne doit jamais être une source
d'erreur.
"""
from __future__ import annotations

import json
import re
import urllib.request

DEPOT = "Hormerty/SecDailyBrief"
URL = f"https://api.github.com/repos/{DEPOT}/releases/latest"
PAGE = f"https://github.com/{DEPOT}/releases/latest"


def numeros(version: str) -> tuple[int, int, int]:
    """« v1.2.0 » ou « 1.2 » → (1, 2, 0). Un suffixe (-beta) est ignoré."""
    chiffres = re.findall(r"\d+", version.split("-")[0])
    valeurs = [int(chiffre) for chiffre in chiffres[:3]]
    return tuple(valeurs + [0] * (3 - len(valeurs)))  # type: ignore[return-value]


def plus_recente(actuelle: str, candidate: str | None) -> bool:
    """La version candidate est-elle strictement plus récente ?"""
    if not candidate:
        return False
    return numeros(candidate) > numeros(actuelle)


def derniere_publiee(timeout: int = 5) -> str | None:
    """Dernier tag publié, ou None si l'API est injoignable ou le dépôt absent."""
    requete = urllib.request.Request(URL, headers={
        "User-Agent": "SecDailyBrief", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(requete, timeout=timeout) as reponse:
            donnees = json.loads(reponse.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    tag = donnees.get("tag_name")
    return tag if isinstance(tag, str) and tag else None
