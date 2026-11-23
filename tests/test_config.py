"""Tests de la configuration de l'application et du périmètre du moteur."""
from __future__ import annotations

from secdailybrief import config, secrets


def test_defauts_appliques_quand_rien_n_est_enregistre(tmp_path):
    lue = config.charger(tmp_path)
    assert lue["smtp_host"] == "smtp.gmail.com"
    assert lue["timezone"] == config.FUSEAU_PAR_DEFAUT
    assert lue["window_hours"] == 27
    assert lue["heure"] == "06:00"


def test_aller_retour(tmp_path):
    config.enregistrer(tmp_path, {"email_user": "bot@example.com", "heure": "07:30"})
    lue = config.charger(tmp_path)
    assert lue["email_user"] == "bot@example.com"
    assert lue["heure"] == "07:30"
    assert lue["smtp_security"] == "ssl", "les défauts survivent à un enregistrement partiel"


def test_ecriture_atomique_sans_residu(tmp_path):
    config.enregistrer(tmp_path, {"email_user": "a@b.c"})
    assert not list(tmp_path.glob("*.tmp")), "aucun fichier temporaire ne doit rester"


def test_aucun_secret_dans_les_reglages():
    """Le fichier de configuration reste lisible : les secrets vont ailleurs, chiffrés."""
    assert not any("password" in cle or "token" in cle or "api_key" in cle
                   for cle in config.DEFAUTS)


def test_validation_accepte_une_configuration_complete():
    assert config.valider({"email_user": "bot@example.com", "heure": "06:00",
                           "window_hours": 27, "smtp_security": "ssl",
                           "timezone": "Europe/Brussels"}) == []


def test_validation_signale_les_champs_fautifs():
    problemes = config.valider({"email_user": "pas-une-adresse", "heure": "25:00",
                                "window_hours": 0, "smtp_security": "aucune",
                                "timezone": "Mars/Olympus"})
    assert "courriel.expediteur" in problemes
    assert "planif.heure" in problemes
    assert "planif.fenetre" in problemes
    assert "planif.fuseau" in problemes


def test_validation_refuse_une_fenetre_trop_large():
    assert "planif.fenetre" in config.valider({"email_user": "a@b.c", "heure": "06:00",
                                               "window_hours": 500,
                                               "smtp_security": "ssl",
                                               "timezone": "Europe/Brussels"})


def test_perimetre_absent_rend_un_dictionnaire_vide(tmp_path):
    assert config.charger_perimetre(tmp_path) == {}


def test_perimetre_filtre_les_sections_inconnues(tmp_path):
    """Le moteur refuse toute section inconnue : on ne lui en écrit jamais."""
    config.enregistrer_perimetre(tmp_path, {
        "stack": {"GitLab": ["gitlab"]},
        "email_user": "ne-doit-pas-sortir",
        "countries": {"DE": None},
    })
    relu = config.charger_perimetre(tmp_path)
    assert set(relu) == {"stack", "countries"}
    assert "email_user" not in relu


def test_jetons_chiffres_et_relus(tmp_path):
    chemin = tmp_path / "secret.dpapi"
    secrets.enregistrer_jetons(chemin, {"smtp_password": "abcd efgh ijkl mnop",
                                        "nvd_api_key": "nvd-123"})
    assert secrets.charger_jetons(chemin) == {"smtp_password": "abcd efgh ijkl mnop",
                                              "nvd_api_key": "nvd-123"}
    assert b"nvd-123" not in chemin.read_bytes()


def test_jetons_absents_rendent_un_dictionnaire_vide(tmp_path):
    assert secrets.charger_jetons(tmp_path / "absent.dpapi") == {}
