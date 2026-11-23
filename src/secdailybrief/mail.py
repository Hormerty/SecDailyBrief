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

    hote = config.get("smtp_host") or "smtp.gmail.com"
    port = port_effectif(config)
    securite = (config.get("smtp_security") or "ssl").lower()
    contexte = ssl.create_default_context()

    if securite == "starttls":
        with smtplib.SMTP(hote, port, timeout=20) as serveur:
            serveur.starttls(context=contexte)
            serveur.login(expediteur, mot_de_passe)
            serveur.sendmail(expediteur, [destinataire], message)
    else:
        with smtplib.SMTP_SSL(hote, port, timeout=20, context=contexte) as serveur:
            serveur.login(expediteur, mot_de_passe)
            serveur.sendmail(expediteur, [destinataire], message)
