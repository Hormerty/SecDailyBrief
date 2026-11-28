"""Sas de sortie : ce qu'il faut avoir regarde avant de publier une version.

Trois questions qu'aucun test ne pose, et qui ont chacune coûte une version :

1. le journal des sept derniers jours contient-il une erreur qui revient ?
2. ce que la documentation affirme est-il encore vrai dans le code ?
3. quelle part de chaque source est retenue ?

    python tools/audit_sortie.py            # tout, sauf le reseau
    python tools/audit_sortie.py --reseau    # verifie aussi que chaque flux repond
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from secdailybrief import paths  # noqa: E402

MOTEUR = Path(r"D:\Security Code GitHub\Sec_Daily_report-")
SEUIL_REPETITION = 3
SEUIL_MORT = 45


def _lignes_journal(jours: int = 7) -> list[str]:
    chemin = paths.chemin_journal()
    if not chemin.is_file():
        return []
    limite = datetime.now() - timedelta(days=jours)
    gardees = []
    for ligne in chemin.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            moment = datetime.strptime(ligne[:19], "%Y-%m-%d %H:%M:%S")
        except ValueError:
            continue
        if moment >= limite:
            gardees.append(ligne)
    return gardees


def erreurs_repetees(jours: int = 7) -> list[tuple[str, int]]:
    """Les messages d'erreur qui reviennent : une panne qui se répète n'est plus un incident."""
    compteur: Counter[str] = Counter()
    for ligne in _lignes_journal(jours):
        if " ERROR " not in ligne and " WARNING " not in ligne:
            continue
        message = ligne[24:].strip()
        # On normalise : un horodatage ou un chemin ne fait pas un message différent.
        message = re.sub(r"\d+", "N", message)
        compteur[message[:120]] += 1
    return [(m, n) for m, n in compteur.most_common() if n >= SEUIL_REPETITION]


def contradictions() -> list[str]:
    """Les affirmations de SOURCES.md que le code contredit."""
    document = MOTEUR / "SOURCES.md"
    if not document.is_file():
        return [f"SOURCES.md introuvable : {document}"]

    import veille  # noqa: PLC0415 - le moteur vit dans l'autre depot

    texte = document.read_text(encoding="utf-8")
    noms_sources = {s["name"] for s in veille.RSS_SOURCES}
    collecteurs = {n for n in dir(veille) if n.startswith("collect_")}
    soucis = []

    # Le statut est declare dans la page par un marqueur, pas devine dans la prose : une
    # explication contient forcement le mot « refuse », et une heuristique s'y trompait.
    for trouve in re.finditer(r"\*\*\[([^\]]+)\]\([^)]+\) <!-- statut: (\w+) -->", texte):
        nom, statut = trouve.group(1), trouve.group(2)
        present = nom in noms_sources or any(nom.lower() in n.lower() for n in collecteurs)
        if statut == "refuse" and present:
            soucis.append(f"{nom} : la page dit « refuse », le moteur l'utilise")
        if statut == "integre" and not present:
            soucis.append(f"{nom} : la page dit « integre », le moteur ne le voit pas")
    return soucis


def rendement(jours: int = 30) -> list[tuple[str, int]]:
    """Sources connues de la base mais sans nouvel article depuis longtemps."""
    base = paths.chemin_etat("stats.db")
    if not base.is_file():
        return []
    try:
        conn = sqlite3.connect(f"file:{base}?mode=ro", uri=True)
        lignes = list(conn.execute(
            "SELECT nom, dernier_article FROM sources WHERE dernier_article IS NOT NULL"))
    except sqlite3.Error:
        return []
    limite = (datetime.now() - timedelta(days=jours)).date()
    mortes = []
    for nom, dernier in lignes:
        try:
            date = datetime.fromisoformat(str(dernier)[:10]).date()
        except ValueError:
            continue
        if date < limite:
            mortes.append((str(nom), (datetime.now().date() - date).days))
    return sorted(mortes, key=lambda kv: -kv[1])


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    parseur.add_argument("--reseau", action="store_true",
                         help="verifie aussi que chaque source configuree repond")
    arguments = parseur.parse_args()

    blocages = 0

    print("== erreurs repetees (7 jours) ==")
    repetees = erreurs_repetees()
    if not repetees:
        print("  aucune")
    for message, nombre in repetees[:10]:
        print(f"  {nombre:3}x {message}")
        blocages += 1

    print()
    print("== documentation contre code ==")
    soucis = contradictions()
    if not soucis:
        print("  aucune contradiction")
    for ligne in soucis:
        print(f"  {ligne}")
        blocages += 1

    print()
    print("== sources sans nouvel article (30 jours) ==")
    mortes = rendement()
    if not mortes:
        print("  aucune")
    for nom, age in mortes[:12]:
        print(f"  {nom:34} {age:4} jours")
        if age >= SEUIL_MORT:
            blocages += 1

    if arguments.reseau:
        print()
        print("== chaque source repond-elle ? ==")
        import feedparser  # noqa: PLC0415
        import requests  # noqa: PLC0415

        import veille  # noqa: PLC0415

        session = requests.Session()
        session.headers.update({"User-Agent": "SecDailyBrief-audit"})
        mortes_reseau = 0
        for source in veille.RSS_SOURCES:
            try:
                reponse = session.get(source["url"], timeout=20)
                flux = feedparser.parse(reponse.content)
                if not flux.entries:
                    print(f"  sans entree : {source['name']}")
                    mortes_reseau += 1
            except requests.RequestException:
                print(f"  injoignable : {source['name']}")
                mortes_reseau += 1
        print(f"  {mortes_reseau} source(s) muette(s) sur {len(veille.RSS_SOURCES)}")
        blocages += mortes_reseau

    print()
    print(f"{blocages} point(s) a regarder avant de publier")
    return 1 if blocages else 0


if __name__ == "__main__":
    sys.exit(main())
