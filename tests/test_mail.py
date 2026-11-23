"""Tests de l'envoi de test : bons paramètres, bon chemin, et l'échec qui remonte."""
from __future__ import annotations

import smtplib

import pytest

from secdailybrief import mail


class _FauxServeur:
    instances: list[_FauxServeur] = []

    def __init__(self, hote, port, timeout=None, context=None):
        self.hote, self.port = hote, port
        self.actions: list[tuple] = []
        _FauxServeur.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *arguments):
        return False

    def login(self, utilisateur, mot_de_passe):
        self.actions.append(("login", utilisateur, mot_de_passe))

    def sendmail(self, expediteur, destinataires, message):
        self.actions.append(("sendmail", expediteur, tuple(destinataires), message))

    def starttls(self, context=None):
        self.actions.append(("starttls",))


@pytest.fixture
def serveur(monkeypatch):
    _FauxServeur.instances.clear()
    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", _FauxServeur)
    monkeypatch.setattr(mail.smtplib, "SMTP", _FauxServeur)
    return _FauxServeur


def test_port_par_defaut_selon_la_securite():
    assert mail.port_effectif({"smtp_security": "ssl"}) == 465
    assert mail.port_effectif({"smtp_security": "starttls"}) == 587
    assert mail.port_effectif({"smtp_security": "ssl", "smtp_port": 2525}) == 2525


def test_envoi_ssl_avec_les_bons_identifiants(serveur):
    mail.tester_envoi({"email_user": "bot@example.com", "recipient_email": "dest@example.com",
                       "smtp_security": "ssl"}, "abcd efgh ijkl mnop")

    instance = serveur.instances[0]
    assert instance.hote == "smtp.gmail.com"
    assert instance.port == 465
    assert ("login", "bot@example.com", "abcd efgh ijkl mnop") in instance.actions
    envois = [action for action in instance.actions if action[0] == "sendmail"]
    assert envois and envois[0][1] == "bot@example.com"


def test_envoi_starttls_passe_par_le_chiffrement(serveur):
    mail.tester_envoi({"email_user": "bot@example.com", "smtp_security": "starttls"},
                      "motdepasse")

    instance = serveur.instances[0]
    assert instance.port == 587
    assert instance.actions[0][0] == "starttls"


def test_destinataire_par_defaut_est_l_expediteur(serveur):
    mail.tester_envoi({"email_user": "bot@example.com"}, "motdepasse")

    envois = [action for action in serveur.instances[0].actions if action[0] == "sendmail"]
    assert envois[0][2] == ("bot@example.com",)


def test_adresse_manquante_refusee():
    with pytest.raises(ValueError):
        mail.tester_envoi({"email_user": ""}, "motdepasse")


def test_echec_d_authentification_remonte(serveur, monkeypatch):
    def refuse(self, utilisateur, mot_de_passe):
        raise smtplib.SMTPAuthenticationError(535, b"nom d'utilisateur ou mot de passe incorrect")

    monkeypatch.setattr(_FauxServeur, "login", refuse)
    with pytest.raises(smtplib.SMTPAuthenticationError):
        mail.tester_envoi({"email_user": "bot@example.com"}, "mauvais")
