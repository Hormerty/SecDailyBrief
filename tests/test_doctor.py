"""Tests du diagnostic : chaque vérification dit la vérité, y compris quand ça va mal."""
from __future__ import annotations

import json

from secdailybrief import doctor
from secdailybrief.doctor import AVERTISSEMENT, OK

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


def test_certificats_tls_verifies(monkeypatch, tmp_path):
    """Le dossier vide : PyInstaller embarque certifi sans son cacert.pem."""
    vide = tmp_path / "cacert.pem"
    vide.write_text("", encoding="utf-8")
    monkeypatch.setattr(doctor, "Path", lambda _chemin: vide)
    import certifi

    monkeypatch.setattr(certifi, "where", lambda: str(vide))

    verification = doctor.verifier_certificats()

    assert verification.statut == doctor.ECHEC
    assert "introuvable" in verification.detail or "suspect" in verification.detail


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

def test_une_erreur_imprevue_ne_sort_pas_en_trace(monkeypatch):
    """PyInstaller affichait « Unhandled exception in script » : on journalise et on rend 1."""
    from secdailybrief import __main__ as point_entree
    from secdailybrief import doctor

    signales = []
    monkeypatch.setattr(point_entree, "_signaler", signales.append)

    def tombe():
        raise OSError("Could not find a suitable TLS CA certificate bundle")

    monkeypatch.setattr(doctor, "executer", tombe)

    assert point_entree.main(["--doctor"]) == 1
    assert len(signales) == 1
    assert isinstance(signales[0], OSError)


def test_le_doctor_signale_un_paquet_de_certificats_absent(monkeypatch, tmp_path):
    """Le diagnostic doit nommer le problème, pas seulement échouer."""
    from secdailybrief import doctor

    monkeypatch.setattr("certifi.where", lambda: str(tmp_path / "absent.pem"))

    verification = doctor.verifier_certificats()

    assert verification.statut != "ok"
    assert "cacert.pem" in verification.detail

# --- Session systemd : les timers partent-ils sans session ouverte ? -----------------------

def test_la_session_linux_signale_un_linger_inactif():
    """Un timer de 06:00 ne part jamais si le gestionnaire utilisateur s'arrête."""
    verification = doctor.verifier_session_linux(linger=lambda: False, wsl=lambda: False)

    assert verification.statut == AVERTISSEMENT
    assert "loginctl enable-linger" in verification.detail


def test_la_session_linux_est_verte_avec_linger():
    verification = doctor.verifier_session_linux(linger=lambda: True, wsl=lambda: False)

    assert verification.statut == OK
    assert "sans session ouverte" in verification.detail


def test_wsl_est_signale_comme_impropre_a_la_planification():
    """WSL arrête la distribution : aucun réglage ne rend les timers fiables."""
    verification = doctor.verifier_session_linux(linger=lambda: True, wsl=lambda: True)

    assert verification.statut == AVERTISSEMENT
    assert "WSL" in verification.detail


def test_la_verification_survit_a_un_systemd_absent():
    def tombe():
        raise OSError("systemctl introuvable")

    verification = doctor.verifier_session_linux(linger=tombe, wsl=lambda: False)

    assert verification.statut == AVERTISSEMENT
    assert "systemctl introuvable" in verification.detail
