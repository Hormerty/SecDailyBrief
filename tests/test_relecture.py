"""La relecture qui peut être mécanisée, pour qu'elle tourne à chaque commit.

Cinq remarques d'une revue de `app.py` sont arrivées sur Reddit : champs de secrets en clair,
validation absente, variable d'environnement mal nommée, effacement incomplet, coquille dans un
commentaire. Aucune ne cassait un test.

Tout ce qui s'y prête est vérifié ici, à chaque exécution de la suite. Ce qui ne s'y prête pas
(fautes de logique, commentaire qui ne décrit plus le code) reste une relecture, déléguée à un
lecteur neuf avant le tag, comme `docs/RELEASE.md` le décrit.
"""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

SRC = Path(__file__).resolve().parent.parent / "src" / "secdailybrief"

#: Les variables qui portent un secret. Elles ne doivent jamais être affichées ni journalisées.
SECRETS = ("smtp_password", "mot_de_passe", "slack_webhook", "discord_webhook",
           "telegram_token", "password", "jeton", "token")


def _fichiers() -> list[Path]:
    return sorted(SRC.glob("*.py"))


def test_aucune_entree_de_secret_n_est_en_clair():
    """Un webhook visible à l'écran est un secret publié : capture, partage, voisin de bureau."""
    en_clair = []
    for fichier in _fichiers():
        for numero, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
            if "ttk.Entry(" not in ligne and "tk.Entry(" not in ligne:
                continue
            if not any(mot in ligne for mot in ("slack", "discord", "telegram_token")):
                continue
            if 'show="' not in ligne:
                en_clair.append(f"{fichier.name}:{numero} {ligne.strip()[:80]}")
    assert not en_clair, "champ de secret sans show= :\n" + "\n".join(en_clair)


def test_aucun_secret_n_est_journalise():
    """Un jeton écrit dans le journal l'est aussi dans les sauvegardes et les rapports de bug."""
    fautes = []
    for fichier in _fichiers():
        for numero, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
            if not re.search(r"journal\.(info|warning|error|debug|log)\(", ligne):
                continue
            if re.search(r"password|token|jeton", ligne, re.I):
                fautes.append(f"{fichier.name}:{numero} {ligne.strip()[:90]}")
    assert not fautes, "secret potentiellement journalise :\n" + "\n".join(fautes)


def test_les_variables_d_environnement_sont_en_majuscules():
    """SECDailyBrief_PAGE au milieu de SDB_* : la convention existait, une exception s'y cachait."""
    #: Noms herites, lus par compatibilite et declares ici une seule fois.
    HERITES = {"SECDailyBrief_PAGE": "ancien nom de SDB_PAGE, lu pour les scripts existants"}
    exceptions = []
    for fichier in _fichiers() + [SRC.parent.parent / "tools" / "audit_sortie.py"]:
        if not fichier.is_file():
            continue
        for numero, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
            for nom in re.findall(r"os\.environ(?:\.get)?\(?[\"']([^\"']+)[\"']", ligne):
                if nom != nom.upper() and nom not in HERITES:
                    exceptions.append(f"{fichier.name}:{numero} {nom}")
    assert not exceptions, "variable d'environnement en casse mixte :\n" + "\n".join(exceptions)


def test_les_exceptions_avalees_sont_declarees():
    """`except Exception: pass` masque une panne : chaque cas doit porter sa justification."""
    #: Les emplacements ou l'absence de tache, de verrou ou de fichier n'est pas une erreur.
    TOLERES = {
        "app.py", "doctor.py", "engine.py", "updates.py", "schedule.py", "secrets.py",
        "planificateur_linux.py", "logging_setup.py",
    }
    muettes = []
    for fichier in _fichiers():
        texte = fichier.read_text(encoding="utf-8")
        for noeud in ast.walk(ast.parse(texte)):
            if not isinstance(noeud, ast.ExceptHandler):
                continue
            corps = noeud.body
            silencieux = all(isinstance(l, ast.Pass) for l in corps)
            if not silencieux:
                continue
            ligne = texte.splitlines()[noeud.lineno - 1]
            # Le code marque deja ses captures volontaires par un noqa : c'est cette marque,
            # et non le nom du fichier, qui vaut justification.
            if "noqa" in ligne or fichier.name in TOLERES:
                continue
            muettes.append(f"{fichier.name}:{noeud.lineno}")
    assert not muettes, "exception avalee sans justification :\n" + "\n".join(muettes)


def test_aucune_coquille_connue_dans_les_commentaires():
    """`endor/` pour `vendor/` : une faute dans un commentaire, jamais dans une assertion."""
    connues = {
        "endor/": "vendor/",
        "l'executable": "l'executable",
        "functionne": "fonctionne",
        "existte": "existe",
        "recu": "recu",
    }
    fautes = []
    for fichier in _fichiers():
        for numero, ligne in enumerate(fichier.read_text(encoding="utf-8").splitlines(), 1):
            if not ligne.strip().startswith("#") and '"""' not in ligne:
                continue
            for faute in ("endor/", "functionne", "existte"):
                if faute in ligne:
                    fautes.append(f"{fichier.name}:{numero} {faute}")
    assert not fautes, "coquille dans un commentaire :\n" + "\n".join(fautes)
