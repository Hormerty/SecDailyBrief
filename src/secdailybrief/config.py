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
    # Alerte immediate toutes les trois heures, en plus du rapport quotidien.
    "alertes_immediates": True,
    # Canaux de l'alerte : le courriel par defaut, les discussions sur demande.
    "alerte_mail": True,
    "alerte_slack": False,
    "alerte_discord": False,
    "alerte_telegram": False,
    "taille_texte": 10,
    # Un consentement donné une fois n'a pas à être redemandé à chaque retour sur la page.
    "consentement": False,
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


def valider_perimetre(perimetre) -> list[str]:
    """Contrôle strict du fichier de périmètre, avant que le moteur ne le découvre.

    Le moteur refuse ce qu'il ne comprend pas, mais son message arrive au moment du run —
    quatre minutes après le clic, dans le journal. Ici, on le dit à l'ouverture, en nommant
    la section fautive.
    """
    if not isinstance(perimetre, dict):
        return ["le fichier doit contenir un objet JSON"]

    problemes: list[str] = []
    for cle in perimetre:
        if cle.startswith("_"):
            continue                    # commentaire libre, toléré
        if cle not in SECTIONS_PERIMETRE:
            problemes.append(f"section inconnue : {cle}")

    pays = perimetre.get("countries")
    if pays is not None and not isinstance(pays, dict):
        problemes.append("countries : objet attendu (code -> fiche)")

    stack = perimetre.get("stack")
    if stack is not None:
        if not isinstance(stack, dict):
            problemes.append("stack : objet attendu (nom -> liste de mots-clés)")
        else:
            for nom, mots in stack.items():
                if not isinstance(nom, str) or not nom.strip():
                    problemes.append("stack : nom de produit vide")
                if (not isinstance(mots, list) or not mots
                        or not all(isinstance(mot, str) and mot.strip() for mot in mots)):
                    problemes.append(f"stack.{nom} : liste de mots-clés non vide attendue")

    cibles = perimetre.get("targets")
    if cibles is not None:
        if not isinstance(cibles, list):
            problemes.append("targets : liste attendue")
        else:
            for position, cible in enumerate(cibles):
                if not isinstance(cible, str) or not cible.strip():
                    problemes.append(f"targets[{position}] : texte non vide attendu")

    return problemes


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


def canaux_invalides(actifs: dict[str, bool], valeurs: dict[str, str]) -> str | None:
    """Ce qui empêcherait un canal de fonctionner : « vide », « url », « jeton » ou None.

    Un webhook et un jeton sont des secrets qu'on ne peut pas deviner : une faute de frappe ne se
    voit pas, elle se traduit par une alerte qui ne part jamais. Ces quatre cas se refusent au
    moment de l'enregistrement, pas trois jours plus tard devant un silence.
    """
    for nom in ("slack", "discord"):
        valeur = (valeurs.get(nom) or "").strip()
        if actifs.get(nom) and not valeur:
            return "vide"
        # On refuse une adresse sans schema, pas une adresse en http : un webhook auto-heberge
        # (Mattermost, proxy interne) est legitimement en http, et le refuser casserait une
        # installation qui marche. La regle sert a attraper une faute de frappe, pas a imposer
        # une politique que le canal distant decide de toute facon.
        if valeur and not valeur.startswith(("http://", "https://")):
            return "url"
    jeton = (valeurs.get("telegram") or "").strip()
    if actifs.get("telegram"):
        if not jeton:
            return "vide"
        if ":" not in jeton or len(jeton) < 20:
            return "jeton"
    return None
