"""Diagnostic : ce qui remplace le support quand l'outil est distribué à des inconnus.

Chaque vérification répond à une question qu'un utilisateur se poserait, et le rapport se
copie-colle dans un ticket. La règle : **ne jamais envoyer de message** — vérifier les
identifiants SMTP ne doit pas remplir la boîte de quelqu'un.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo

from . import config as configuration
from . import engine, logging_setup, mail, paths, plateforme, runner, schedule, secrets

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


def verifier_import_moteur() -> Verification:
    """Le moteur s'importe-t-il vraiment ? Un fichier présent ne suffit pas.

    C'est la vérification qui aurait attrapé le premier exe livré : `vendor/veille.py` était
    là, son empreinte était bonne, et il était inimportable — `feedparser` manquait dans le
    binaire. Le symptôme visible était une stack vide.
    """
    try:
        module = engine.module()
        produits = len(module.STACK_PRODUCTS)
    except Exception as exc:      # noqa: BLE001 - l'exception est le résultat
        return Verification("Moteur importable", ECHEC, f"{type(exc).__name__}: {exc}")
    return Verification("Moteur importable", OK,
                        f"{produits} produits, dependances presentes")


def verifier_certificats() -> Verification:
    """Les racines TLS sont-elles dans le binaire ?

    PyInstaller embarque le paquet `certifi` mais pas toujours son `cacert.pem` : le
    dossier existe, vide, et la première requête HTTPS échoue avec « Could not find a
    suitable TLS CA certificate bundle ». C'est arrivé au premier vrai rapport.
    """
    import certifi

    chemin = Path(certifi.where())
    if not chemin.exists():
        return Verification("Certificats TLS", ECHEC, f"cacert.pem introuvable : {chemin}")
    taille = chemin.stat().st_size
    if taille < 10_000:
        return Verification("Certificats TLS", ECHEC, f"cacert.pem suspect : {taille} octets")
    return Verification("Certificats TLS", OK, f"{chemin.name}, {taille} octets")


def verifier_dossier(dossier: Path) -> Verification:
    try:
        paths.s_assurer_dossier()
    except OSError as exc:
        return Verification("Dossier de donnees", ECHEC, str(exc))
    # Le mode compte : en portable, les donnees voyagent avec le programme et disparaissent
    # si l'on efface le dossier. Le dire evite de croire qu'une sauvegarde est faite ailleurs.
    if paths.est_portable():
        mode = "portable"
    elif sys.platform == "win32":
        mode = "profil Windows"
    else:
        mode = "profil utilisateur"
    return Verification("Dossier de donnees", OK, f"{dossier} ({mode})")


def verifier_configuration(reglages: dict) -> Verification:
    problemes = configuration.valider(reglages)
    if problemes:
        return Verification("Configuration", ECHEC, ", ".join(problemes))
    return Verification("Configuration", OK,
                        f"{reglages.get('email_user')} -> {reglages.get('recipient_email')}")


def verifier_secret(jetons: dict) -> Verification:
    if not jetons.get("smtp_password"):
        return Verification("Mot de passe", ECHEC, "aucun mot de passe enregistre")
    if sys.platform == "win32":
        return Verification("Mot de passe", OK, "chiffre DPAPI, dechiffrable par ce compte")
    # Sous Linux, le secret vit dans le trousseau du bureau ou, a defaut, dans un fichier 0600.
    # Annoncer « DPAPI » la-bas etait faux, et le diagnostic doit dire ce qui est.
    return Verification("Mot de passe", OK,
                        "protege par le trousseau du bureau, ou fichier 0600 a defaut")


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


def verifier_planificateur(existe=None, prochaine=None, existe_alerte=None) -> Verification:
    existe = existe or schedule.existe
    prochaine = prochaine or schedule.prochaine_execution
    existe_alerte = existe_alerte or (
        lambda: schedule.existe(schedule.NOM_TACHE_ALERTE))
    try:
        if not existe():
            return Verification("Planificateur", AVERTISSEMENT, "aucune tache enregistree")
        moment = prochaine()
        # La tache d'alerte est optionnelle : son absence n'est pas un defaut, mais son etat
        # merite d'etre dit, sinon un utilisateur croit recevoir des alertes qui n'existent pas.
        try:
            alerte = "alertes actives" if existe_alerte() else "alertes inactives"
        except Exception:         # noqa: BLE001
            alerte = "etat des alertes inconnu"
    except Exception as exc:      # noqa: BLE001 - planificateur indisponible
        return Verification("Planificateur", AVERTISSEMENT, f"{type(exc).__name__}: {exc}")
    return Verification("Planificateur", OK,
                        f"prochaine execution : {moment or 'inconnue'} · {alerte}")


def verifier_session_linux(linger=None, wsl=None) -> Verification:
    """Les timers systemd ne partent que si le gestionnaire utilisateur tourne.

    Sous Linux, `systemctl --user` arrête son gestionnaire dès qu'aucune session n'est ouverte.
    Un timer de 06:00 ne se déclenche alors jamais, sans que rien ne le signale : la tâche
    existe, elle est active, et elle ne part pas. `loginctl enable-linger` corrige cela.

    Dans WSL, la distribution s'arrête d'elle-même après quelques secondes d'inactivité : aucun
    réglage ne rend la planification fiable. Le dire vaut mieux que de le laisser découvrir.
    """
    linger = linger if linger is not None else plateforme.linger_actif
    wsl = wsl if wsl is not None else plateforme.dans_wsl
    try:
        dans_wsl = bool(wsl())
        actif = bool(linger())
    except Exception as exc:              # noqa: BLE001 - systemd absent ou refusant
        return Verification("Session systemd", AVERTISSEMENT, f"{type(exc).__name__}: {exc}")
    if dans_wsl:
        return Verification("Session systemd", AVERTISSEMENT,
                            "WSL arrete la distribution quand rien ne tourne : "
                            "les timers ne partiront pas seuls")
    if actif:
        return Verification("Session systemd", OK,
                            "linger actif : les timers partent sans session ouverte")
    utilisateur = os.environ.get("USER") or os.environ.get("LOGNAME") or "<utilisateur>"
    return Verification("Session systemd", AVERTISSEMENT,
                        f"linger inactif : les timers ne partiront pas sans session "
                        f"ouverte (loginctl enable-linger {utilisateur})")


def collecter(dossier: Path | None = None, *, reglages: dict | None = None,
              jetons: dict | None = None, tester_reseau=None,
              tester_smtp=None, tache_existe=None, prochaine=None) -> list[Verification]:
    dossier = dossier or paths.dossier_donnees()
    reglages = configuration.charger(dossier) if reglages is None else reglages
    jetons = secrets.charger_jetons(paths.chemin_secret()) if jetons is None else jetons
    mot_de_passe = jetons.get("smtp_password", "")
    return [
        verifier_moteur(),
        verifier_import_moteur(),
        verifier_certificats(),
        verifier_dossier(dossier),
        verifier_configuration(reglages),
        verifier_secret(jetons),
        verifier_fuseau(reglages),
        verifier_reseau(tester_reseau),
        verifier_smtp(reglages, mot_de_passe, tester_smtp),
        verifier_planificateur(tache_existe, prochaine),
        *([verifier_session_linux()] if sys.platform != "win32" else []),
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
