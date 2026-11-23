"""Récupère le moteur depuis le dépôt public, à un commit épinglé, et vérifie son intégrité.

Le moteur n'est pas copié à la main : il est téléchargé à un SHA de commit précis, son
empreinte est enregistrée dans vendor/engine.json, et `--verify` rejoue le contrôle à tout
moment. Un fichier modifié à la main ne correspond plus au verrou — c'est le garde-fou
contre une retouche accidentelle de vendor/veille.py.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DEPOT = "Hormerty/Sec_Daily_report-"
URL = "https://raw.githubusercontent.com/{depot}/{sha}/veille.py"
RACINE = Path(__file__).resolve().parent.parent
VENDOR = RACINE / "vendor"
FICHIER = VENDOR / "veille.py"
VERROU = VENDOR / "engine.json"


def empreinte(donnees: bytes) -> str:
    return hashlib.sha256(donnees).hexdigest()


def telecharger(sha: str) -> bytes:
    requete = urllib.request.Request(
        URL.format(depot=DEPOT, sha=sha), headers={"User-Agent": "SecDailyBrief-build"})
    with urllib.request.urlopen(requete, timeout=30) as reponse:
        return reponse.read()


def enregistrer(sha: str, donnees: bytes) -> None:
    VENDOR.mkdir(parents=True, exist_ok=True)
    FICHIER.write_bytes(donnees)
    VERROU.write_text(json.dumps({
        "depot": DEPOT,
        "commit": sha,
        "sha256": empreinte(donnees),
        "octets": len(donnees),
        "recupere_le": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def verifier() -> int:
    if not VERROU.exists() or not FICHIER.exists():
        print("vendor/veille.py ou vendor/engine.json manquant : lancer --sha <commit>",
              file=sys.stderr)
        return 1
    verrou = json.loads(VERROU.read_text(encoding="utf-8"))
    attendu = verrou["sha256"]
    reel = empreinte(FICHIER.read_bytes())
    if attendu != reel:
        print(f"Empreinte differente de celle du verrou.\n  attendu : {attendu}\n  reel    : {reel}",
              file=sys.stderr)
        return 1
    print(f"OK: {FICHIER.relative_to(RACINE)} correspond au commit {verrou['commit']} "
          f"({verrou['octets']} octets)")
    return 0


def main() -> int:
    parseur = argparse.ArgumentParser(description=__doc__)
    groupe = parseur.add_mutually_exclusive_group(required=True)
    groupe.add_argument("--sha", help="commit du depot a epingler")
    groupe.add_argument("--verify", action="store_true", help="verifier le fichier present")
    arguments = parseur.parse_args()

    if arguments.verify:
        return verifier()

    donnees = telecharger(arguments.sha)
    enregistrer(arguments.sha, donnees)
    print(f"OK: {len(donnees)} octets recuperes au commit {arguments.sha} "
          f"-> {FICHIER.relative_to(RACINE)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
