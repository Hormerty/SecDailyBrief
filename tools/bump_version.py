"""Monte la version d'un cran, partout où elle est écrite.

Trois fichiers portent la version — le paquet, les propriétés Windows du fichier .exe, et
`pyproject.toml` — plus le titre du README de l'archive. Quatre endroits, donc quatre
occasions de se tromper : la 1.2.0 est partie avec un README qui annonçait 1.1.0.

La règle de numérotation est celle du propriétaire du dépôt :

    1.4.1   correction, ou ajout de langues
    1.5.0   nouvelle fonctionnalité visible
    2.0.0   changement incompatible (format de données, configuration)

Usage :
    python tools/bump_version.py patch        # 1.4.0 -> 1.4.1
    python tools/bump_version.py minor        # 1.4.1 -> 1.5.0
    python tools/bump_version.py major        # 1.5.0 -> 2.0.0
    python tools/bump_version.py patch --dry-run
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
INIT = RACINE / "src" / "secdailybrief" / "__init__.py"
PYPROJECT = RACINE / "pyproject.toml"
VERSION_TXT = RACINE / "build" / "version.txt"
README_TXT = RACINE / "build" / "README.txt"


def version_actuelle() -> str:
    texte = INIT.read_text(encoding="utf-8")
    trouve = re.search(r'__version__ = "([^"]+)"', texte)
    if not trouve:
        raise SystemExit("version introuvable dans src/secdailybrief/__init__.py")
    return trouve.group(1)


def suivante(version: str, cran: str) -> str:
    majeur, mineur, correctif = (int(partie) for partie in version.split("."))
    if cran == "major":
        return f"{majeur + 1}.0.0"
    if cran == "minor":
        return f"{majeur}.{mineur + 1}.0"
    return f"{majeur}.{mineur}.{correctif + 1}"


def _remplacer(chemin: Path, motif: str, remplacement: str, texte: str) -> str:
    # re.MULTILINE : sans lui, un motif ancré par ^ ne trouve que le début du fichier, et
    # « ^version = … » manquait la ligne au milieu de pyproject.toml.
    nouveau, compte = re.subn(motif, remplacement, texte, flags=re.MULTILINE)
    if compte == 0:
        raise SystemExit(f"motif introuvable dans {chemin.relative_to(RACINE)} : {motif}")
    return nouveau


def appliquer(nouvelle: str, essai: bool = False) -> list[str]:
    """Écrit la version partout ; renvoie la liste des fichiers touchés."""
    ancienne = version_actuelle()
    majeur, mineur, correctif = nouvelle.split(".")
    modifs: list[str] = []

    init = INIT.read_text(encoding="utf-8")
    init = _remplacer(INIT, r'__version__ = "[^"]+"', f'__version__ = "{nouvelle}"', init)
    modifs.append(str(INIT.relative_to(RACINE)))

    projet = PYPROJECT.read_text(encoding="utf-8")
    projet = _remplacer(PYPROJECT, r'^version = "[^"]+"', f'version = "{nouvelle}"',
                        projet, )
    modifs.append(str(PYPROJECT.relative_to(RACINE)))

    ressources = VERSION_TXT.read_text(encoding="utf-8")
    tuple_version = f"({majeur}, {mineur}, {correctif}, 0)"
    ressources = _remplacer(VERSION_TXT, r"filevers=\([^)]+\)", f"filevers={tuple_version}",
                            ressources)
    ressources = _remplacer(VERSION_TXT, r"prodvers=\([^)]+\)", f"prodvers={tuple_version}",
                            ressources)
    ressources = _remplacer(VERSION_TXT, r"StringStruct\('FileVersion', '[^']+'\)",
                            f"StringStruct('FileVersion', '{nouvelle}.0')", ressources)
    ressources = _remplacer(VERSION_TXT, r"StringStruct\('ProductVersion', '[^']+'\)",
                            f"StringStruct('ProductVersion', '{nouvelle}.0')", ressources)
    modifs.append(str(VERSION_TXT.relative_to(RACINE)))

    # Le README de l'archive annonce la version dans son titre, souligné par des « = » de la
    # même longueur : les deux lignes doivent suivre ensemble.
    readme = README_TXT.read_text(encoding="utf-8")
    titre = f"SecDailyBrief {nouvelle}"
    readme = _remplacer(README_TXT, r"SecDailyBrief \d+\.\d+\.\d+\n=+", f"{titre}\n{'=' * len(titre)}",
                        readme)
    modifs.append(str(README_TXT.relative_to(RACINE)))

    if not essai:
        for chemin, contenu in ((INIT, init), (PYPROJECT, projet),
                                (VERSION_TXT, ressources), (README_TXT, readme)):
            chemin.write_text(contenu, encoding="utf-8")
    print(f"{ancienne} -> {nouvelle}" + (" (essai, rien écrit)" if essai else ""))
    return modifs


def main() -> int:
    analyseur = argparse.ArgumentParser(description="Monte la version du projet.")
    analyseur.add_argument("cran", choices=("patch", "minor", "major"))
    analyseur.add_argument("--dry-run", action="store_true", help="afficher sans écrire")
    arguments = analyseur.parse_args()

    nouvelle = suivante(version_actuelle(), arguments.cran)
    for chemin in appliquer(nouvelle, essai=arguments.dry_run):
        print(f"  {chemin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
