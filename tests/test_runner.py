"""Tests du lanceur : pré-vol, environnement, exécution, journal."""
from __future__ import annotations

import contextlib
import sys

import pytest

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
