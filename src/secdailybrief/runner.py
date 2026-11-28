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

import json
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


def canaux_alerte(config: dict, jetons: dict[str, str] | None = None) -> list[dict]:
    """Canaux de discussion actifs, sous la forme attendue par le moteur (variable WEBHOOKS).

    Le webhook *est* le secret : l'URL suffit à publier. Il est donc rangé avec le mot de
    passe SMTP, chiffré par DPAPI, et jamais dans config.json.
    """
    jetons = jetons or {}
    cibles: list[dict] = []
    if config.get("alerte_slack") and jetons.get("slack_webhook"):
        cibles.append({"type": "slack", "url": jetons["slack_webhook"]})
    if config.get("alerte_discord") and jetons.get("discord_webhook"):
        cibles.append({"type": "discord", "url": jetons["discord_webhook"]})
    if config.get("alerte_telegram") and jetons.get("telegram_token") and jetons.get("telegram_chat"):
        cibles.append({"type": "telegram", "token": jetons["telegram_token"],
                       "chat": jetons["telegram_chat"]})
    return cibles


def environnement(config: dict, mot_de_passe: str, dossier: Path,
                  jetons: dict[str, str] | None = None,
                  journal: logging.Logger | None = None) -> dict[str, str]:
    """Environnement du processus enfant, construit explicitement.

    Les variables EMAIL_* et SMTP_* héritées du shell sont retirées : sur un poste de
    développement elles traîneraient sinon d'un test à l'autre, et l'utilisateur ne
    saurait plus quelle configuration a réellement servi.
    """
    # Sans ce repli, `journal.warning` levait un NameError dans le chemin de secours des
    # certificats : le message d'aide devenait une panne. Le defaut est le journal du module,
    # et `executer` passe le sien.
    journal = journal or logging.getLogger(__name__)
    # Les variables d'un secret ne doivent pas entrer dans l'environnement de l'enfant par
    # heritage : une variable parasite de l'hote ferait passer une cle qu'on croyait absente.
    env = {cle: valeur for cle, valeur in os.environ.items()
           if not cle.startswith(("EMAIL_", "SMTP_", "WEBHOOKS", "NVD_API_KEY",
                                  "RANSOMWARE_API_KEY", "GITHUB_TOKEN"))}
    # « requests » cherche son paquet de certificats dans l'environnement. Dans un binaire fige,
    # il ne le trouve pas toujours seul : « Could not find a suitable TLS CA certificate
    # bundle », une execution morte en 0,1 s et aucun rapport envoye. On le lui donne.
    try:
        import certifi

        cacert = certifi.where()
        if Path(cacert).is_file():
            env["REQUESTS_CA_BUNDLE"] = cacert
            env["SSL_CERT_FILE"] = cacert
        else:
            journal.warning("cacert.pem absent : %s", cacert)
    except Exception as exc:                 # noqa: BLE001 - certifi absent : on continue
        journal.warning("Paquet de certificats introuvable : %s", exc)
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
        "ALERT_MAIL": "1" if config.get("alerte_mail", True) else "0",
    })
    cibles = canaux_alerte(config, jetons)
    if cibles:
        env["WEBHOOKS"] = json.dumps(cibles, ensure_ascii=False)
    if config.get("smtp_port"):
        env["SMTP_PORT"] = str(config["smtp_port"])
    if config.get("window_hours"):
        env["WINDOW_HOURS"] = str(config["window_hours"])
    for cle_config, cle_env in (("nvd_api_key", "NVD_API_KEY"),
                                ("ransomware_api_key", "RANSOMWARE_API_KEY"),
                                ("github_token", "GITHUB_TOKEN")):
        # Une cle d'API est un secret : elle vit dans le magasin chiffre. La lire dans
        # config.json la laissait en clair sur le disque, alors que le mot de passe SMTP et les
        # webhooks sont ranges ailleurs. L'ancien emplacement reste lu, en le signalant.
        valeur = (jetons or {}).get(cle_config)
        if not valeur and config.get(cle_config):
            journal.warning(
                "%s trouvee dans config.json : deplacez-la dans le magasin chiffre.", cle_config)
            valeur = config[cle_config]
        if valeur:
            env[cle_env] = valeur
    return env


MODES = {
    "run": [],
    "alerte": ["--alerte"],
    "preview": ["--preview"],
    "sources": ["--check-feeds"],
    "liens": ["--check-links"],
}

#: Modes qui envoient quelque chose. Eux seuls ont besoin du mot de passe : l'exiger pour
#: « tester les sources » fermait deux boutons qui n'envoient rien, avec un message de
#: courriel en échec.
MODES_ENVOI = frozenset({"run", "alerte"})


def exige_mot_de_passe(mode: str) -> bool:
    return mode in MODES_ENVOI


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
             preflight: bool = True,
             jetons: dict[str, str] | None = None,
             origine: str = "") -> Resultat:
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

        env = environnement(config, mot_de_passe, dossier, jetons, journal)
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
            historique.enregistrer(statut, duree, mode, origine=origine)
        except OSError as exc:                  # disque plein, dossier en lecture seule…
            journal.warning("Historique non enregistre : %s", exc)
        return Resultat(statut, code, duree, lignes)
