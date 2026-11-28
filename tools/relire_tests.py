"""Repere les tests qui recopient une valeur du code au lieu d'enoncer une intention.

Un test comme `assert "<Duration>P1D</Duration>" in xml` ne protège rien : il fige la valeur que
le code produit aujourd'hui, y compris quand cette valeur est un défaut. Il a fallu le casser pour
découvrir que la tâche d'alerte mourait au bout d'un jour.

Le partage n'est pas « le littéral existe-t-il dans le code », sinon les noms d'étiquettes XML et
les clés i18n, qui sont de vrais contrats, seraient signalés par dizaines. Ce qui trahit une
transcription, c'est une **valeur** :

- un élément XML porteur de contenu (`<Tag>valeur</Tag>`) et non un nom d'élément ;
- une chaîne qui contient un chiffre ou une unité (`PT3H`, `2026-11-26T09:17:00`) ;
- une phrase entière (plus de 30 caracteres avec des espaces).

    python tools/relire_tests.py
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SOURCE = RACINE / "src" / "secdailybrief"
TESTS = RACINE / "tests"

ELEMENT_AVEC_CONTENU = re.compile(r"<([A-Za-z][\w:.-]*)>([^<]+)</\1>")
CONTENU_TECHNIQUE = re.compile(r"\d|[A-Z]{2,}H|PT\d")


def _sources() -> dict[str, str]:
    return {p.name: p.read_text(encoding="utf-8") for p in sorted(SOURCE.glob("*.py"))}


def suspects() -> list[tuple[str, int, str, str, str]]:
    """(fichier de test, ligne, littéral, fichier source, motif de soupçon)."""
    sources = _sources()
    trouves = []
    for fichier in sorted(TESTS.glob("test_*.py")):
        texte = fichier.read_text(encoding="utf-8")
        lignes = texte.splitlines()
        for noeud in ast.walk(ast.parse(texte)):
            if not isinstance(noeud, ast.Constant) or not isinstance(noeud.value, str):
                continue
            litteral = noeud.value
            if len(litteral) < 6 or "\n" in litteral:
                continue
            for nom, contenu in sources.items():
                if litteral not in contenu:
                    continue
                if ELEMENT_AVEC_CONTENU.search(litteral):
                    motif = "element XML porteur de valeur"
                elif CONTENU_TECHNIQUE.search(litteral) and len(litteral) <= 30:
                    motif = "valeur chiffree ou unité"
                elif len(litteral) > 30 and " " in litteral:
                    motif = "phrase recopiee"
                else:
                    break        # nom d'étiquette, clé i18n, identifiant : contrat legitime
                ligne = lignes[noeud.lineno - 1].strip() if noeud.lineno <= len(lignes) else ""
                trouves.append((fichier.name, noeud.lineno, litteral, nom, f"{motif} | {ligne[:70]}"))
                break
    return trouves


def main() -> int:
    trouves = suspects()
    print(f"{len(trouves)} littéral(aux) à relire : une valeur recopiée depuis le code\n")
    for fichier, ligne, litteral, source, motif in trouves:
        print(f"  {fichier}:{ligne}")
        print(f"    {litteral!r}  (aussi dans {source})")
        print(f"    {motif}\n")
    if not trouves:
        print("  aucun. Les tests qui restent portent sur des noms, pas sur des valeurs.")
    return 1 if trouves else 0


if __name__ == "__main__":
    sys.exit(main())
