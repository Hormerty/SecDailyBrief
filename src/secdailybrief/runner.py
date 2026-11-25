"""Lanceur : pré-vol réseau, environnement du moteur, sous-processus, journal.

C'est la pièce qui transforme un fichier de configuration en une exécution. Trois choix
y sont volontaires :

* **le mot de passe passe par l'environnement du processus enfant, jamais par la ligne de
  commande** — les arguments d'un processus sont visibles dans le gestionnaire de tâches ;
* **le moteur tourne dans le dossier de données**, pas dans celui du programme : ses
  fichiers d'état (seen.json, stats.db…) y vivent, et un dossier en lecture seule échoue
  au démarrage plutôt qu'au milieu d'un run ;
* **le pré-vol répond à une question simple** — le réseau est-il joignable ? — et non
  « les sources sont-elles saines ? ». Une source en panne est un problème du moteur ; un
  réseau absent est un problème de moment, et le créneau suivant réessaiera.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import requests

from . import historique, lock, paths

URLS_TEMOIN = (
    "https://cert.cyber.gouv.fr/feed/",
    "https://www.cisa.gov/sites/default/files/feeds/known_exploited_vulnerabilities.json",
)
DELAI_SONDE = 5
ESSAIS_SONDE = 2
FUSEAU_PAR_DEFAUT = "Europe/Brussels"

_NIVEAUX = {
    "DEBUG": logging.DEBUG, "INFO": logging.INFO, "WARNING": logging.WARNING,
    "WARN": logging.WARNING, "ERROR": logging.ERROR, "CRITICAL": logging.CRITICAL,
}


@dataclass
class Resultat:
    """Ce qu'une exécution a produit, pour que le panneau puisse le dire en une phrase."""

    statut: str                     # ok | deja_en_cours | reseau | erreur
    code: int | None = None
    duree: float = 0.0
    lignes: list[str] = field(default_factory=list)


def reseau_disponible(urls=URLS_TEMOIN, delai: int = DELAI_SONDE,
                      essais: int = ESSAIS_SONDE) -> bool:
    """Vrai dès qu'une des URLs témoins répond : le réseau existe, les sources feront leur vie."""
    for _ in range(essais):
        for url in urls:
            try:
                reponse = requests.get(url, timeout=delai,
                                       headers={"User-Agent": "SecDailyBrief"})
            # OSError couvre le cas où le paquet de certificats manque : ssl lève un OSError,
            # pas une RequestException, et la sonde faisait tomber l'application entière.
            except (requests.RequestException, OSError):
                continue
            if reponse.status_code < 400:
                return True
    return False


def environnement(config: dict, mot_de_passe: str, dossier: Path) -> dict[str, str]:
    """Environnement du processus enfant, construit explicitement.

    Les variables EMAIL_* et SMTP_* héritées du shell sont retirées : sur un poste de
    développement elles traîneraient sinon d'un test à l'autre, et l'utilisateur ne
    saurait plus quelle configuration a réellement servi.
    """
    env = {cle: valeur for cle, valeur in os.environ.items()
           if not cle.startswith(("EMAIL_", "SMTP_"))}
    env.update({
        "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8",
        "TZ": config.get("timezone") or FUSEAU_PAR_DEFAUT,
        "CONFIG_FILE": str(dossier / "perimetre.json"),
        "EMAIL_USER": config["email_user"],
        "RECIPIENT_EMAIL": config.get("recipient_email") or config["email_user"],
        "EMAIL_PASSWORD": mot_de_passe,
        "SMTP_HOST": config.get("smtp_host") or "smtp.gmail.com",
        "SMTP_SECURITY": config.get("smtp_security") or "ssl",
    })
    if config.get("smtp_port"):
        env["SMTP_PORT"] = str(config["smtp_port"])
    if config.get("window_hours"):
        env["WINDOW_HOURS"] = str(config["window_hours"])
    for cle_config, cle_env in (("nvd_api_key", "NVD_API_KEY"),
                                ("ransomware_api_key", "RANSOMWARE_API_KEY"),
                                ("github_token", "GITHUB_TOKEN")):
        if config.get(cle_config):
            env[cle_env] = config[cle_config]
    return env


MODES = {
    "run": [],
    "preview": ["--preview"],
    "sources": ["--check-feeds"],
    "liens": ["--check-links"],
}


def commande_moteur(mode: str = "run") -> list[str]:
    """Comment lancer le moteur, selon qu'on est en développement ou dans l'exécutable figé."""
    if getattr(sys, "frozen", False):
        # PyInstaller : pas d'interpréteur séparé, c'est l'exécutable qui se relance.
        base = [sys.executable, "--moteur"]
    else:
        base = [sys.executable, str(paths.dossier_executable() / "vendor" / "veille.py")]
    return base + MODES.get(mode, [])


def commande_application(mode: str = "run") -> list[str]:
    """Comment lancer l'application elle-même, et non le moteur nu.

    C'est ce que la tâche planifiée doit exécuter : passer par `--run` garantit le pré-vol
    réseau, le verrou mono-instance, le journal et le bon répertoire de travail. Appeler
    `--moteur` court-circuite tout cela — la première tâche créée le faisait, et le rapport
    de 06:00 serait parti dans le vide.
    """
    if getattr(sys, "frozen", False):
        return [sys.executable, f"--{mode}"]
    return [sys.executable, "-m", "secdailybrief", f"--{mode}"]


_TRACEBACK = "Traceback (most recent call last):"


def _niveau(ligne: str) -> int:
    """Niveau de la ligne : celui qu'elle annonce, ou ERROR pour une trace Python.

    Sans ça, une exception du moteur — qui n'écrit pas « ERROR » avant sa trace — se
    retrouverait en INFO, et le panneau la noierait dans le flot du rapport.
    """
    if ligne.startswith(_TRACEBACK):
        return logging.ERROR
    return _NIVEAUX.get(ligne.split(" ", 1)[0].upper(), logging.INFO)


def _decoder(brut: bytes) -> str:
    """Décode une ligne du moteur, en UTF-8 ou, à défaut, dans le code page de Windows.

    Le journal affichait « NVD (�diteurs) » : l'accent du moteur arrivait dans un encodage que
    le décodage UTF-8 strict ne reconnaissait pas, et le remplacement muet produisait U+FFFD.
    On essaie l'UTF-8 d'abord — c'est ce que PYTHONIOENCODING demande — puis on retombe sur
    cp1252, qui est ce que Windows écrit quand la consigne n'est pas suivie.
    """
    try:
        return brut.decode("utf-8")
    except UnicodeDecodeError:
        return brut.decode("cp1252", "replace")


def executer(config: dict, mot_de_passe: str, journal: logging.Logger, *,
             mode: str = "run", dossier: Path | None = None,
             preflight: bool = True) -> Resultat:
    """Une exécution complète : verrou, pré-vol, moteur, journal.

    `preflight=False` sert aux diagnostics — « tester les sources » doit pouvoir tourner
    précisément quand le réseau est douteux, sinon il ne sert à rien.
    """
    dossier = dossier or paths.s_assurer_dossier()

    with lock.instance_unique() as seule:
        if not seule:
            journal.warning("Une autre execution est deja en cours.")
            return Resultat("deja_en_cours")

        if preflight and not reseau_disponible():
            journal.warning("Reseau injoignable : execution reportee, la journee reste ouverte.")
            return Resultat("reseau")

        env = environnement(config, mot_de_passe, dossier)
        debut = time.monotonic()
        processus = subprocess.Popen(
            commande_moteur(mode), cwd=str(dossier), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

        lignes: list[str] = []
        assert processus.stdout is not None
        for brut in processus.stdout:
            ligne = _decoder(brut).rstrip("\r\n")
            if not ligne:
                continue
            lignes.append(ligne)
            # Le moteur préfixe déjà ses lignes d'un niveau : le garder donnerait
            # « INFO INFO score 4 … ». On le retire, le journal remet le sien.
            tete, _, reste = ligne.partition(" ")
            if tete.upper() in _NIVEAUX:
                journal.log(_NIVEAUX[tete.upper()], "%s", reste.lstrip())
            else:
                journal.log(_niveau(ligne), "%s", ligne)

        code = processus.wait()
        duree = time.monotonic() - debut
        statut = "ok" if code == 0 else "erreur"
        if code == 0:
            journal.info("Moteur termine : code=%s, duree=%.1fs, mode=%s", code, duree, mode)
        else:
            journal.error("Moteur termine en erreur : code=%s, duree=%.1fs, mode=%s",
                          code, duree, mode)
        # Une ligne pour l'historique : c'est ce qui permet de repondre « le rapport est-il
        # parti hier ? » sans ouvrir le journal.
        try:
            historique.enregistrer(statut, duree, mode)
        except OSError as exc:                  # disque plein, dossier en lecture seule…
            journal.warning("Historique non enregistre : %s", exc)
        return Resultat(statut, code, duree, lignes)
