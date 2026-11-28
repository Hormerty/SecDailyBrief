"""Tests du lanceur : pré-vol, environnement, exécution, journal."""
from __future__ import annotations

import contextlib
import sys

import pytest

from secdailybrief import config as configuration
from secdailybrief import lock, logging_setup, runner

# Le verrou est un mutex Windows nommé : si l'application tourne pendant les tests — ce qui
# arrive quand on la teste justement — tous les cas partent en « deja_en_cours ».
REEL = lock.instance_unique


@pytest.fixture(autouse=True)
def verrou_isole(monkeypatch):
    @contextlib.contextmanager
    def libre(nom=lock.NOM_PAR_DEFAUT):
        yield True

    monkeypatch.setattr(runner.lock, "instance_unique", libre)

CONFIG = {
    "email_user": "bot@example.com",
    "recipient_email": "dest@example.com",
    "timezone": "Europe/Brussels",
    "window_hours": 27,
    "nvd_api_key": "nvd-123",
}


class _Reponse:
    def __init__(self, code: int) -> None:
        self.status_code = code


def test_reseau_disponible_des_qu_une_source_repond(monkeypatch):
    def faux_get(url, **kwargs):
        if "cisa" in url:
            return _Reponse(200)
        raise runner.requests.ConnectionError("injoignable")

    monkeypatch.setattr(runner.requests, "get", faux_get)
    assert runner.reseau_disponible() is True


def test_reseau_indisponible_quand_tout_echoue(monkeypatch):
    def faux_get(url, **kwargs):
        raise runner.requests.ConnectionError("injoignable")

    monkeypatch.setattr(runner.requests, "get", faux_get)
    assert runner.reseau_disponible() is False


def test_environnement_porte_les_secrets_et_ecarte_le_shell(tmp_path, monkeypatch):
    monkeypatch.setenv("EMAIL_PASSWORD", "vieux-secret-du-shell")
    monkeypatch.setenv("SMTP_HOST", "smtp.autre-fournisseur.fr")

    env = runner.environnement(CONFIG, "mot-de-passe-dpapi", tmp_path)

    assert env["EMAIL_PASSWORD"] == "mot-de-passe-dpapi", "l'environnement hérité ne doit pas gagner"
    assert env["SMTP_HOST"] == "smtp.gmail.com", "la valeur du shell doit être écartée"
    assert env["EMAIL_USER"] == "bot@example.com"
    assert env["RECIPIENT_EMAIL"] == "dest@example.com"
    assert env["CONFIG_FILE"] == str(tmp_path / "perimetre.json"), \
        "le moteur reçoit le périmètre, pas les réglages de l'interface"
    assert env["NVD_API_KEY"] == "nvd-123"
    assert env["PYTHONUTF8"] == "1"


def test_la_commande_du_moteur_ne_contient_aucun_secret():
    commande = runner.commande_moteur("run")
    assert all("mot-de-passe" not in argument for argument in commande)
    assert commande[-1] != "--preview"


def test_mode_apercu_transmet_l_option():
    assert "--preview" in runner.commande_moteur("preview")


def test_execution_journalise_la_sortie_du_moteur(tmp_path, monkeypatch):
    faux_moteur = tmp_path / "faux_moteur.py"
    faux_moteur.write_text(
        "import sys\n"
        "print('INFO Daily report already sent on 2026-11-22: nothing to do.')\n"
        "print('WARNING Feed A: timeout')\n"
        "sys.exit(0)\n", encoding="utf-8")
    monkeypatch.setattr(runner, "commande_moteur",
                        lambda mode="run": [sys.executable, str(faux_moteur)])
    monkeypatch.setattr(runner, "reseau_disponible", lambda *a, **k: True)
    journal = logging_setup.journaliser(tmp_path / "journal.log")

    resultat = runner.executer(CONFIG, "motdepasse", journal, dossier=tmp_path)

    assert resultat.statut == "ok"
    assert resultat.code == 0
    assert len(resultat.lignes) == 2
    contenu = (tmp_path / "journal.log").read_text(encoding="utf-8")
    assert "Daily report already sent" in contenu
    assert "WARNING" in contenu


def test_execution_refusee_si_une_autre_tourne(tmp_path, monkeypatch):
    monkeypatch.setattr(runner.lock, "instance_unique", REEL)
    monkeypatch.setattr(runner, "reseau_disponible", lambda *a, **k: True)
    journal = logging_setup.journaliser(tmp_path / "journal.log")

    with REEL() as seule:
        if not seule:
            pytest.skip("une instance de l'application tourne en ce moment")
        assert seule is True
        resultat = runner.executer(CONFIG, "motdepasse", journal, dossier=tmp_path)

    assert resultat.statut == "deja_en_cours"


def test_execution_reportee_sans_reseau(tmp_path, monkeypatch):
    monkeypatch.setattr(runner, "reseau_disponible", lambda *a, **k: False)
    journal = logging_setup.journaliser(tmp_path / "journal.log")

    resultat = runner.executer(CONFIG, "motdepasse", journal, dossier=tmp_path)

    assert resultat.statut == "reseau"
    assert "Reseau injoignable" in (tmp_path / "journal.log").read_text(encoding="utf-8")


def test_une_trace_python_du_moteur_est_journalisee_en_erreur(tmp_path, monkeypatch):
    """Une exception du moteur n'annonce pas « ERROR » : elle doit quand même ressortir."""
    faux_moteur = tmp_path / "moteur_en_echec.py"
    faux_moteur.write_text(
        "import sys\n"
        "print('Traceback (most recent call last):')\n"
        "print('veille.ConfigurationError: section inconnue : section_bidon')\n"
        "sys.exit(1)\n", encoding="utf-8")
    monkeypatch.setattr(runner, "commande_moteur",
                        lambda mode="run": [sys.executable, str(faux_moteur)])
    monkeypatch.setattr(runner, "reseau_disponible", lambda *a, **k: True)
    journal = logging_setup.journaliser(tmp_path / "journal.log")

    resultat = runner.executer(CONFIG, "motdepasse", journal, dossier=tmp_path)

    assert resultat.statut == "erreur"
    assert resultat.code == 1
    contenu = (tmp_path / "journal.log").read_text(encoding="utf-8")
    assert "ERROR" in contenu
    assert "Moteur termine en erreur" in contenu

def test_le_decodeur_accepte_utf8_et_cp1252():
    """Le journal affichait « NVD (�diteurs) » : les deux encodages doivent être lus."""
    texte = "NVD (éditeurs): 8 new"

    assert runner._decoder(texte.encode("utf-8")) == texte
    assert runner._decoder(texte.encode("cp1252")) == texte
    assert runner._decoder(b"ascii seulement") == "ascii seulement"


def test_le_mode_alerte_passe_le_drapeau_au_moteur():
    """La tâche d'alerte doit lancer le moteur dans son mode, pas le mode rapport."""
    assert runner.MODES["alerte"] == ["--alerte"]
    assert runner.MODES["run"] == []


def test_la_commande_d_alerte_passe_par_l_application():
    """Comme pour --run : pré-vol, verrou, journal et dossier de données restent en place."""
    commande = runner.commande_application("alerte")

    assert commande[-1] == "--alerte"


def test_le_mode_alerte_est_active_par_defaut(monkeypatch, tmp_path):
    assert configuration.DEFAUTS["alertes_immediates"] is True
    assert configuration.charger(tmp_path)["alertes_immediates"] is True

def test_le_mode_alerte_appelle_bien_la_fonction_d_alerte_du_moteur(monkeypatch):
    """Le 26 novembre, --alerte appelait main() et envoyait un rapport complet."""
    from secdailybrief import __main__ as point_entree

    appels = []

    class ModuleFactice:
        def main(self):
            appels.append("rapport")
            return 0

        def main_alert(self):
            appels.append("alerte")
            return 0

    monkeypatch.setattr(point_entree.engine, "module", lambda: ModuleFactice())
    monkeypatch.setattr(point_entree.logging_setup, "journaliser", lambda chemin: None)

    assert point_entree.executer_moteur("alerte") == 0
    assert appels == ["alerte"]
    assert point_entree.executer_moteur("rapport") == 0
    assert appels == ["alerte", "rapport"]


# --- Canaux d'alerte : courriel, Slack, Discord, Telegram -----------------------------------

def test_les_canaux_suivent_les_cases_et_les_secrets():
    config = {"alerte_slack": True, "alerte_discord": False, "alerte_telegram": True}
    jetons = {"slack_webhook": "https://hooks.slack.com/x",
              "telegram_token": "T", "telegram_chat": "42"}

    cibles = runner.canaux_alerte(config, jetons)

    assert [c["type"] for c in cibles] == ["slack", "telegram"]
    assert cibles[0]["url"].startswith("https://hooks.slack.com/")
    assert cibles[1]["chat"] == "42"


def test_une_case_cochee_sans_secret_ne_cree_pas_de_canal():
    """Cocher Slack sans webhook ne doit pas produire un canal vide."""
    config = {"alerte_slack": True, "alerte_discord": True, "alerte_telegram": True}

    assert runner.canaux_alerte(config, {}) == []


def test_l_environnement_porte_les_webhooks_et_le_choix_du_courriel(tmp_path):
    config = dict(CONFIG)
    config.update({"alerte_mail": False, "alerte_slack": True})
    jetons = {"slack_webhook": "https://hooks.slack.com/x"}

    env = runner.environnement(config, "motdepasse", tmp_path, jetons)

    assert env["ALERT_MAIL"] == "0"
    assert "hooks.slack.com" in env["WEBHOOKS"]
    # Aucun secret ne doit fuir dans une variable héritée du shell.
    assert "EMAIL_PASSWORD" in env and env["EMAIL_PASSWORD"] == "motdepasse"

# --- Boutons « Sources » et « Liens » du panneau -------------------------------------------

def test_les_verifications_du_moteur_ont_un_mode():
    """Sans entrée dans MODES, les boutons ne lançaient rien."""
    assert runner.MODES["sources"] == ["--check-feeds"]
    assert runner.MODES["liens"] == ["--check-links"]


def test_seuls_les_modes_qui_envoient_exigent_le_mot_de_passe():
    """Tester les sources n'envoie aucun courriel : le mot de passe n'a rien à y faire."""
    assert runner.exige_mot_de_passe("run")
    assert runner.exige_mot_de_passe("alerte")
    assert not runner.exige_mot_de_passe("sources")
    assert not runner.exige_mot_de_passe("liens")
    assert not runner.exige_mot_de_passe("preview")


def test_l_application_accepte_les_drapeaux_du_moteur(monkeypatch):
    """L'exécutable figé rejetait « --check-feeds » : unrecognized arguments."""
    from secdailybrief import __main__ as point_entree

    appels = []
    monkeypatch.setattr(point_entree, "executer_moteur", lambda mode: appels.append(mode) or 0)

    assert point_entree.main(["--moteur", "--check-feeds"]) == 0
    assert point_entree.main(["--moteur", "--check-links"]) == 0
    assert point_entree.main(["--moteur", "--alerte"]) == 0
    assert appels == ["sources", "liens", "alerte"]


def test_executer_moteur_appelle_les_bonnes_fonctions(monkeypatch):
    from secdailybrief import __main__ as point_entree

    appels = []

    class Module:
        def check_feeds(self):
            appels.append("feeds")
            return 0

        def check_links(self):
            appels.append("liens")
            return 0

        def main(self):
            appels.append("rapport")
            return 0

        def main_alert(self):
            appels.append("alerte")
            return 0

    monkeypatch.setattr(point_entree.engine, "module", lambda: Module())
    monkeypatch.setattr(point_entree.logging_setup, "journaliser", lambda chemin: None)

    point_entree.executer_moteur("sources")
    point_entree.executer_moteur("liens")
    point_entree.executer_moteur("rapport")

    assert appels == ["feeds", "liens", "rapport"]

# --- Remarques sur runner.py --------------------------------------------------------------

def _config(**extra):
    base = {"email_user": "a@b.c", "timezone": "Europe/Brussels"}
    base.update(extra)
    return base


def test_environnement_fonctionne_sans_journal(tmp_path):
    """Il levait un NameError dans le chemin de secours des certificats : l'aide devenait une panne."""
    from pathlib import Path

    from secdailybrief import runner

    env = runner.environnement(_config(), "motdepasse", Path("."), {})
    assert env["EMAIL_PASSWORD"] == "motdepasse"


def test_sans_cacert_l_environnement_ne_leve_pas(tmp_path, monkeypatch):
    from pathlib import Path

    from secdailybrief import runner

    monkeypatch.setattr("certifi.where", lambda: str(tmp_path / "absent.pem"))
    env = runner.environnement(_config(), "x", Path("."), {})
    assert "REQUESTS_CA_BUNDLE" not in env      # absent : rien n'est pose, rien ne casse


def test_une_cle_api_vient_du_magasin_chiffre(tmp_path, monkeypatch):
    from pathlib import Path

    from secdailybrief import runner

    env = runner.environnement(_config(nvd_api_key="depuis-config"), "x", Path("."),
                               {"nvd_api_key": "depuis-coffre"})
    assert env["NVD_API_KEY"] == "depuis-coffre"


def test_une_cle_api_restee_dans_config_est_signalee(tmp_path):
    from pathlib import Path

    import logging

    from secdailybrief import runner

    journal = logging.getLogger("test-runner-revue")
    enregistre = []
    journal.warning = lambda *a, **k: enregistre.append(a[0] % a[1:] if len(a) > 1 else a[0])

    env = runner.environnement(_config(github_token="en-clair"), "x", Path("."), {}, journal)

    assert env["GITHUB_TOKEN"] == "en-clair"          # compatibilite : la cle passe encore
    assert any("config.json" in message for message in enregistre)   # mais on le dit


def test_les_variables_heritees_de_secrets_ne_passent_pas(tmp_path, monkeypatch):
    """Une variable parasite de l'hote ferait passer une cle qu'on croyait absente."""
    from pathlib import Path

    from secdailybrief import runner

    monkeypatch.setenv("GITHUB_TOKEN", "jeton-de-l-hote")
    monkeypatch.setenv("NVD_API_KEY", "cle-de-l-hote")
    env = runner.environnement(_config(), "x", Path("."), {})
    assert "GITHUB_TOKEN" not in env
    assert "NVD_API_KEY" not in env
