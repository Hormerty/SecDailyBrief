"""Tests du diagnostic : chaque vérification dit la vérité, y compris quand ça va mal."""
from __future__ import annotations

import json

from secdailybrief import doctor

CONFIG = {
    "email_user": "bot@example.com",
    "recipient_email": "dest@example.com",
    "timezone": "Europe/Brussels",
    "window_hours": 27,
    "heure": "06:00",
    "smtp_security": "ssl",
}


def test_moteur_verifie_par_empreinte():
    verification = doctor.verifier_moteur()
    assert verification.statut == doctor.OK
    assert "empreinte verifiee" in verification.detail


def test_moteur_altere_est_signale(tmp_path, monkeypatch):
    (tmp_path / "veille.py").write_text("print('pas le vrai moteur')", encoding="utf-8")
    (tmp_path / "engine.json").write_text(json.dumps({
        "commit": "abc1234", "sha256": "0" * 64, "octets": 10}), encoding="utf-8")
    monkeypatch.setattr(doctor.engine, "dossier", lambda: tmp_path)

    verification = doctor.verifier_moteur()

    assert verification.statut == doctor.ECHEC
    assert "empreinte differente" in verification.detail


def test_moteur_importable_signale_une_dependance_absente(monkeypatch):
    """Le cas du premier binaire : fichier présent, empreinte bonne, import impossible."""
    def echoue(*arguments, **options):
        raise ModuleNotFoundError("No module named 'feedparser'")

    monkeypatch.setattr(doctor.engine, "module", echoue)

    verification = doctor.verifier_import_moteur()

    assert verification.statut == doctor.ECHEC
    assert "feedparser" in verification.detail


def test_configuration_incomplete_signalee():
    verification = doctor.verifier_configuration({"email_user": "", "heure": "99:99"})
    assert verification.statut == doctor.ECHEC
    assert "courriel.expediteur" in verification.detail


def test_configuration_complete_acceptee():
    assert doctor.verifier_configuration(CONFIG).statut == doctor.OK


def test_secret_absent_signale():
    verification = doctor.verifier_secret({})
    assert verification.statut == doctor.ECHEC
    assert "aucun mot de passe" in verification.detail


def test_fuseau_inconnu_signale():
    verification = doctor.verifier_fuseau({"timezone": "Mars/Olympus"})
    assert verification.statut == doctor.ECHEC


def test_reseau_et_smtp_avec_des_sondes_injectees():
    assert doctor.verifier_reseau(lambda: True).statut == doctor.OK
    assert doctor.verifier_reseau(lambda: False).statut == doctor.ECHEC

    def smtp_en_echec(config, mot_de_passe):
        raise ConnectionRefusedError("port ferme")

    verification = doctor.verifier_smtp(CONFIG, "motdepasse", smtp_en_echec)
    assert verification.statut == doctor.ECHEC
    assert "ConnectionRefusedError" in verification.detail


def test_smtp_sans_mot_de_passe_est_un_avertissement():
    assert doctor.verifier_smtp(CONFIG, "").statut == doctor.AVERTISSEMENT


def test_planificateur_absent_est_un_avertissement():
    verification = doctor.verifier_planificateur(lambda: False, lambda: None)
    assert verification.statut == doctor.AVERTISSEMENT


def test_rapport_resume_les_comptes():
    verifications = [
        doctor.Verification("A", doctor.OK, "bon"),
        doctor.Verification("B", doctor.ECHEC, "mauvais"),
        doctor.Verification("C", doctor.AVERTISSEMENT, "moyen"),
    ]
    texte = doctor.rapport(verifications)
    assert "[ok]" in texte and "[echec]" in texte and "[!]" in texte
    assert "3 verifications, 1 echec(s), 1 avertissement(s)" in texte


def test_collecter_de_bout_en_bout_avec_des_sondes(tmp_path):
    verifications = doctor.collecter(
        dossier=tmp_path, reglages=CONFIG, jetons={"smtp_password": "motdepasse"},
        tester_reseau=lambda: True, tester_smtp=lambda config, mot: None,
        tache_existe=lambda: True, prochaine=lambda: "2026-11-24T06:00:00")
    echecs = [v.nom for v in verifications if v.statut == doctor.ECHEC]
    assert echecs == [], echecs
