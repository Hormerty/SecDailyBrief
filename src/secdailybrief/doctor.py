"""Diagnostic : ce qui remplace le support quand l'outil est distribué à des inconnus.

Chaque vérification répond à une question qu'un utilisateur se poserait, et le rapport se
copie-colle dans un ticket. La règle : **ne jamais envoyer de message** — vérifier les
identifiants SMTP ne doit pas remplir la boîte de quelqu'un.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config as configuration
from . import engine, logging_setup, mail, paths, runner, schedule, secrets

OK = "ok"
AVERTISSEMENT = "avertissement"
ECHEC = "echec"


@dataclass
class Verification:
    nom: str
    statut: str
    detail: str


def verifier_moteur() -> Verification:
    """Le fichier épinglé est-il celui que le verrou décrit ?"""
    dossier = engine.dossier()
    fichier = dossier / "veille.py"
    verrou = dossier / "engine.json"
    if not fichier.exists() or not verrou.exists():
        return Verification("Moteur", ECHEC, "veille.py ou engine.json absent")
    try:
        attendu = json.loads(verrou.read_text(encoding="utf-8"))
        reel = hashlib.sha256(fichier.read_bytes()).hexdigest()
    except (OSError, json.JSONDecodeError) as exc:
        return Verification("Moteur", ECHEC, f"verrou illisible : {exc}")
    if reel != attendu.get("sha256"):
        return Verification("Moteur", ECHEC,
                            f"empreinte differente du verrou ({attendu.get('commit', '?')})")
    return Verification("Moteur", OK,
                        f"commit {attendu['commit']}, {attendu['octets']} octets, empreinte verifiee")


def verifier_dossier(dossier: Path) -> Verification:
    try:
        paths.s_assurer_dossier()
    except OSError as exc:
        return Verification("Dossier de donnees", ECHEC, str(exc))
    return Verification("Dossier de donnees", OK, str(dossier))


def verifier_configuration(reglages: dict) -> Verification:
    problemes = configuration.valider(reglages)
    if problemes:
        return Verification("Configuration", ECHEC, ", ".join(problemes))
    return Verification("Configuration", OK,
                        f"{reglages.get('email_user')} -> {reglages.get('recipient_email')}")


def verifier_secret(jetons: dict) -> Verification:
    if not jetons.get("smtp_password"):
        return Verification("Mot de passe", ECHEC, "aucun mot de passe enregistre")
    return Verification("Mot de passe", OK, "chiffre DPAPI, dechiffrable par ce compte")


def verifier_fuseau(reglages: dict) -> Verification:
    nom = reglages.get("timezone")
    try:
        fuseau = ZoneInfo(nom)
    except Exception as exc:      # noqa: BLE001 - fuseau inconnu : c'est le diagnostic
        return Verification("Fuseau horaire", ECHEC, f"{nom} introuvable ({exc})")
    if str(fuseau) == "UTC" and nom != "UTC":
        return Verification("Fuseau horaire", AVERTISSEMENT,
                            f"{nom} resolu en UTC : tzdata manque ?")
    return Verification("Fuseau horaire", OK, str(fuseau))


def verifier_reseau(tester=None) -> Verification:
    tester = tester or runner.reseau_disponible
    return (Verification("Reseau", OK, "au moins une source repond")
            if tester() else
            Verification("Reseau", ECHEC, "aucune source joignable"))


def verifier_smtp(reglages: dict, mot_de_passe: str, tester=None) -> Verification:
    if not mot_de_passe:
        return Verification("SMTP", AVERTISSEMENT, "verification impossible sans mot de passe")
    tester = tester or mail.verifier_connexion
    try:
        tester(reglages, mot_de_passe)
    except Exception as exc:      # noqa: BLE001 - tout echec se rapporte tel quel
        return Verification("SMTP", ECHEC, f"{type(exc).__name__}: {exc}")
    return Verification("SMTP", OK, "connexion et authentification acceptees")


def verifier_planificateur(existe=None, prochaine=None) -> Verification:
    existe = existe or schedule.existe
    prochaine = prochaine or schedule.prochaine_execution
    try:
        if not existe():
            return Verification("Planificateur", AVERTISSEMENT, "aucune tache enregistree")
        moment = prochaine()
    except Exception as exc:      # noqa: BLE001 - planificateur indisponible
        return Verification("Planificateur", AVERTISSEMENT, f"{type(exc).__name__}: {exc}")
    return Verification("Planificateur", OK, f"prochaine execution : {moment or 'inconnue'}")


def collecter(dossier: Path | None = None, *, reglages: dict | None = None,
              jetons: dict | None = None, tester_reseau=None,
              tester_smtp=None, tache_existe=None, prochaine=None) -> list[Verification]:
    dossier = dossier or paths.dossier_donnees()
    reglages = configuration.charger(dossier) if reglages is None else reglages
    jetons = secrets.charger_jetons(paths.chemin_secret()) if jetons is None else jetons
    mot_de_passe = jetons.get("smtp_password", "")
    return [
        verifier_moteur(),
        verifier_dossier(dossier),
        verifier_configuration(reglages),
        verifier_secret(jetons),
        verifier_fuseau(reglages),
        verifier_reseau(tester_reseau),
        verifier_smtp(reglages, mot_de_passe, tester_smtp),
        verifier_planificateur(tache_existe, prochaine),
    ]


def rapport(verifications: list[Verification]) -> str:
    symboles = {OK: "[ok]   ", AVERTISSEMENT: "[!]    ", ECHEC: "[echec]"}
    lignes = [f"{symboles.get(v.statut, '[?]')} {v.nom:<20} {v.detail}" for v in verifications]
    echecs = sum(1 for v in verifications if v.statut == ECHEC)
    avertissements = sum(1 for v in verifications if v.statut == AVERTISSEMENT)
    lignes.append("")
    lignes.append(f"{len(verifications)} verifications, {echecs} echec(s), "
                  f"{avertissements} avertissement(s)")
    return "\n".join(lignes)


def executer() -> int:
    """Mode `--doctor` : imprime le rapport et sort en erreur s'il y a un échec."""
    verifications = collecter()
    texte = rapport(verifications)
    print(texte)
    journal = logging_setup.journaliser(paths.chemin_journal())
    journal.info("Diagnostic\n%s", texte)
    return 1 if any(v.statut == ECHEC for v in verifications) else 0
