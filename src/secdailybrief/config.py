"""Configuration de l'application : réglages d'un côté, périmètre de l'autre.

Deux fichiers, et c'est volontaire :

* `config.json` porte les réglages de l'application — adresses, SMTP, fuseau, heure,
  fenêtre. C'est l'application qui le lit, personne d'autre ;
* `perimetre.json` contient exactement les trois sections que le moteur accepte
  (`countries`, `stack`, `targets`) et lui est passé par `CONFIG_FILE`. Le moteur refuse
  toute section inconnue, et c'est une qualité : on ne la dilue pas en y versant les
  réglages de l'interface.

**Aucun secret n'est écrit ici.** Les mots de passe et jetons passent par DPAPI, dans un
fichier séparé ; un JSON lisible qui contiendrait un jeton annulerait la précaution.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

FUSEAU_PAR_DEFAUT = "Europe/Brussels"
HEURE_VALIDE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
SECURITES_SMTP = ("ssl", "starttls")
SECTIONS_PERIMETRE = ("countries", "stack", "targets")

DEFAUTS: dict = {
    "langue": None,                 # None = suivre Windows au premier lancement
    "email_user": "",
    "recipient_email": "",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": None,
    "smtp_security": "ssl",
    "timezone": FUSEAU_PAR_DEFAUT,
    "window_hours": 27,
    "heure": "06:00",
    "taille_texte": 10,
}


def chemin_config(dossier: Path) -> Path:
    return dossier / "config.json"


def chemin_perimetre(dossier: Path) -> Path:
    return dossier / "perimetre.json"


def _lire(chemin: Path) -> dict:
    if not chemin.exists():
        return {}
    try:
        return json.loads(chemin.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"{chemin.name} illisible (JSON invalide, ligne {exc.lineno})") from exc


def _ecrire(chemin: Path, donnees: dict) -> None:
    """Écrit par fichier temporaire puis remplace : jamais de configuration à moitié écrite."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    temporaire = chemin.with_suffix(chemin.suffix + ".tmp")
    temporaire.write_text(json.dumps(donnees, indent=2, ensure_ascii=False) + "\n",
                          encoding="utf-8")
    os.replace(temporaire, chemin)


def charger(dossier: Path) -> dict:
    """Réglages enregistrés, complétés par les valeurs par défaut."""
    config = dict(DEFAUTS)
    config.update(_lire(chemin_config(dossier)))
    return config


def enregistrer(dossier: Path, config: dict) -> None:
    reglages = {cle: valeur for cle, valeur in config.items() if cle in DEFAUTS}
    _ecrire(chemin_config(dossier), reglages)


def valider(config: dict) -> list[str]:
    """Liste des problèmes, en clair et dans l'ordre de l'écran. Vide = tout va bien."""
    problemes: list[str] = []
    expediteur = (config.get("email_user") or "").strip()
    if "@" not in expediteur:
        problemes.append("courriel.expediteur")
    destinataire = (config.get("recipient_email") or "").strip()
    if destinataire and "@" not in destinataire:
        problemes.append("courriel.destinataire")
    if not HEURE_VALIDE.match((config.get("heure") or "").strip()):
        problemes.append("planif.heure")
    try:
        heures = int(config.get("window_hours"))
        if not 1 <= heures <= 168:
            problemes.append("planif.fenetre")
    except (TypeError, ValueError):
        problemes.append("planif.fenetre")
    if (config.get("smtp_security") or "").lower() not in SECURITES_SMTP:
        problemes.append("courriel.motdepasse")
    if not _fuseau_valide(config.get("timezone")):
        problemes.append("planif.fuseau")
    return problemes


def _fuseau_valide(nom: str | None) -> bool:
    from zoneinfo import ZoneInfo

    if not nom:
        return False
    try:
        ZoneInfo(nom)
    except Exception:       # noqa: BLE001 - nom de fuseau invalide, c'est le cas à traiter
        return False
    return True


def charger_perimetre(dossier: Path) -> dict:
    """Périmètre enregistré, ou {} : le moteur retombera alors sur ses valeurs par défaut."""
    chemin = chemin_perimetre(dossier)
    if not chemin.exists():
        return {}
    donnees = _lire(chemin)
    return {cle: valeur for cle, valeur in donnees.items() if cle in SECTIONS_PERIMETRE}


def enregistrer_perimetre(dossier: Path, perimetre: dict) -> None:
    """N'écrit que les sections reconnues par le moteur ; une faute ici serait refusée au run."""
    propre = {cle: valeur for cle, valeur in perimetre.items() if cle in SECTIONS_PERIMETRE}
    _ecrire(chemin_perimetre(dossier), propre)
