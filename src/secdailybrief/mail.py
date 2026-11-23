"""Envoi d'un message de test, avec exactement les paramètres que le moteur utilisera.

Le test sert à une chose : distinguer tout de suite une adresse fausse, un mot de passe de
compte au lieu d'un mot de passe d'application, ou un port bloqué — plutôt que de le
découvrir le lendemain à 06:00, dans un journal que personne ne lit.
"""
from __future__ import annotations

import smtplib
import ssl

SUJET = "SecDailyBrief — test"
CORPS = (
    "Ceci est un message de test envoyé par SecDailyBrief.\n\n"
    "Si vous le recevez, votre configuration est correcte : le rapport quotidien "
    "arrivera à cette adresse.\n"
)


def port_effectif(config: dict) -> int:
    if config.get("smtp_port"):
        return int(config["smtp_port"])
    return 587 if (config.get("smtp_security") or "ssl").lower() == "starttls" else 465


def _ouvrir(config: dict, mot_de_passe: str):
    """Ouvre une session SMTP authentifiée. À utiliser avec `with` (quit à la sortie)."""
    expediteur = (config.get("email_user") or "").strip()
    if not expediteur:
        raise ValueError("adresse d'envoi manquante")

    hote = config.get("smtp_host") or "smtp.gmail.com"
    port = port_effectif(config)
    securite = (config.get("smtp_security") or "ssl").lower()
    contexte = ssl.create_default_context()

    if securite == "starttls":
        serveur = smtplib.SMTP(hote, port, timeout=20)
        serveur.starttls(context=contexte)
        serveur.login(expediteur, mot_de_passe)
        return serveur
    serveur = smtplib.SMTP_SSL(hote, port, timeout=20, context=contexte)
    serveur.login(expediteur, mot_de_passe)
    return serveur


def verifier_connexion(config: dict, mot_de_passe: str) -> None:
    """Connexion et authentification seulement — aucun message n'est envoyé.

    C'est ce que le diagnostic utilise : vérifier les identifiants ne doit pas remplir la
    boîte de l'utilisateur d'un message de plus.
    """
    with _ouvrir(config, mot_de_passe) as _serveur:
        pass


def tester_envoi(config: dict, mot_de_passe: str) -> None:
    """Envoie un message réel ; laisse remonter l'exception SMTP en cas d'échec."""
    expediteur = (config.get("email_user") or "").strip()
    destinataire = (config.get("recipient_email") or expediteur).strip()
    if not expediteur or not destinataire:
        raise ValueError("adresse d'envoi ou de réception manquante")

    message = ("From: {expediteur}\r\nTo: {destinataire}\r\nSubject: {sujet}\r\n"
               "MIME-Version: 1.0\r\nContent-Type: text/plain; charset=utf-8\r\n\r\n{corps}"
               ).format(expediteur=expediteur, destinataire=destinataire,
                        sujet=SUJET, corps=CORPS).encode("utf-8")

    with _ouvrir(config, mot_de_passe) as serveur:
        serveur.sendmail(expediteur, [destinataire], message)
