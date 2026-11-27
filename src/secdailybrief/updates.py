"""Sait s'il existe une version plus récente publiée sur GitHub.

Aucun serveur à nous : la dernière release est lue par l'API publique de GitHub. Le jour où le
dépôt n'existe pas encore, ou quand la machine est hors ligne, la fonction renvoie None et
l'interface n'affiche rien. Un bandeau de mise à jour ne doit jamais être une source d'erreur.

Les empreintes sont lues dans le même appel : c'est l'API qui publie le `digest` de chaque
archive. Demander à l'utilisateur d'aller les chercher sur la page des versions, c'est lui
demander de sauter l'étape de vérification.
"""
from __future__ import annotations

import json
import re
import sys
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


def nom_archive(version: str, plateforme: str | None = None,
                portable: bool = False) -> str:
    """Nom de l'archive qui correspond à cette machine, tel que publié.

    Les quatre noms sont construits par la CI ; les reproduire ici évite d'afficher une
    empreinte qui ne correspond à aucun fichier téléchargeable.
    """
    systeme = plateforme or sys.platform
    suffixe = "-portable" if portable else ""
    if systeme.startswith("win"):
        return f"SecDailyBrief-{version}-win64{suffixe}.zip"
    return f"SecDailyBrief-{version}-linux-x86_64{suffixe}.tar.gz"


def derniere_release(timeout: int = 5) -> dict | None:
    """« {'tag': 'v1.7.5', 'empreintes': {nom: sha256}} », ou None si l'API est injoignable."""
    requete = urllib.request.Request(URL, headers={
        "User-Agent": "SecDailyBrief", "Accept": "application/vnd.github+json"})
    try:
        with urllib.request.urlopen(requete, timeout=timeout) as reponse:
            donnees = json.loads(reponse.read().decode("utf-8"))
    except (OSError, ValueError):
        return None
    if not isinstance(donnees, dict):
        return None
    tag = donnees.get("tag_name")
    if not isinstance(tag, str) or not tag:
        return None
    empreintes: dict[str, str] = {}
    for archive in donnees.get("assets") or []:
        if not isinstance(archive, dict):
            continue
        nom = archive.get("name")
        empreinte = str(archive.get("digest") or "")
        if isinstance(nom, str) and empreinte.startswith("sha256:"):
            empreintes[nom] = empreinte.split(":", 1)[1]
    return {"tag": tag, "empreintes": empreintes}


def derniere_publiee(timeout: int = 5) -> str | None:
    """Dernier tag publié, ou None. Conservé pour le bandeau de démarrage."""
    release = derniere_release(timeout=timeout)
    return release["tag"] if release else None
