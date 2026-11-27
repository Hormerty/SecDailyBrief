"""Tests du socle : chemins, secrets, journal, verrou mono-instance."""
from __future__ import annotations

import re
import sys

import pytest

from secdailybrief import lock, logging_setup, paths, secrets

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="API Windows")


# --- chemins ---------------------------------------------------------------

def test_environment_impose_le_dossier(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.VARIABLE_DONNEES, str(tmp_path / "donnees"))
    assert paths.dossier_donnees() == tmp_path / "donnees"
    assert paths.chemin_config() == tmp_path / "donnees" / "config.json"
    assert paths.chemin_secret() == tmp_path / "donnees" / "secret.dpapi"
    assert paths.chemin_etat("seen.json") == tmp_path / "donnees" / "seen.json"


def test_dossier_cree_au_besoin_et_inscriptible(monkeypatch, tmp_path):
    monkeypatch.setenv(paths.VARIABLE_DONNEES, str(tmp_path / "donnees"))
    dossier = paths.s_assurer_dossier()
    assert dossier.is_dir()
    assert not (dossier / ".ecriture").exists(), "la sonde d'écriture doit être retirée"


def test_marqueur_portable_deplace_les_donnees(monkeypatch, tmp_path):
    monkeypatch.delenv(paths.VARIABLE_DONNEES, raising=False)
    (tmp_path / paths.MARQUEUR_PORTABLE).write_text("", encoding="utf-8")
    monkeypatch.setattr(paths, "dossier_executable", lambda: tmp_path)
    assert paths.est_portable()
    assert paths.dossier_donnees() == tmp_path / "data"


def test_defaut_dans_appdata(monkeypatch, tmp_path):
    """Le dossier par défaut suit le système : profil Windows, ou XDG sous Linux."""
    monkeypatch.delenv(paths.VARIABLE_DONNEES, raising=False)
    monkeypatch.setenv("APPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setattr(paths, "est_portable", lambda: False)

    assert paths.dossier_donnees() == tmp_path / paths.NOM_APPLICATION


# --- secrets ---------------------------------------------------------------

@windows_only
def test_aller_retour_du_secret(tmp_path):
    chemin = tmp_path / "secret.dpapi"
    secrets.enregistrer(chemin, "abcd efgh ijkl mnop")
    assert secrets.charger(chemin) == "abcd efgh ijkl mnop"


@windows_only
def test_le_mot_de_passe_n_apparait_pas_en_clair(tmp_path):
    chemin = tmp_path / "secret.dpapi"
    secrets.enregistrer(chemin, "abcd efgh ijkl mnop")
    brut = chemin.read_bytes()
    assert b"abcd efgh" not in brut
    assert b"abcd" not in brut


@windows_only
def test_secret_absent_rend_none(tmp_path):
    assert secrets.charger(tmp_path / "absent.dpapi") is None


@windows_only
def test_secret_altere_est_refuse(tmp_path):
    """DPAPI signe le chiffré : une altération doit être détectée, pas déchiffrée."""
    import base64

    chemin = tmp_path / "secret.dpapi"
    secrets.enregistrer(chemin, "motdepasse")
    chiffre = bytearray(base64.b64decode(chemin.read_bytes()))
    chiffre[len(chiffre) // 2] ^= 0xFF
    chemin.write_bytes(base64.b64encode(bytes(chiffre)))
    with pytest.raises(OSError):
        secrets.charger(chemin)


# --- journal ---------------------------------------------------------------

def test_journal_horodate_et_utf8(tmp_path):
    chemin = tmp_path / "journal.log"
    logger = logging_setup.journaliser(chemin)
    logger.info("Ligne accentuée : éàü 🔴")
    logger.warning("Avertissement")
    contenu = chemin.read_text(encoding="utf-8")
    assert "éàü 🔴" in contenu
    assert re.search(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO\s+Ligne accentuée",
                     contenu, re.MULTILINE)
    assert "WARNING" in contenu


def test_ligne_du_moteur_horodatee():
    ligne = logging_setup.ligne_horodatee("INFO Report size: 129.3 KB\n")
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} INFO\s+Report size", ligne)
    assert "\n" not in ligne


def test_ligne_sans_niveau_reste_lisible():
    ligne = logging_setup.ligne_horodatee("Traceback (most recent call last):")
    assert "Traceback (most recent call last):" in ligne
    assert re.match(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", ligne)


# --- verrou ----------------------------------------------------------------

@windows_only
def test_deuxieme_instance_refusee():
    nom = "Local\\SecDailyBrief-test"
    with lock.instance_unique(nom) as premiere:
        assert premiere is True
        with lock.instance_unique(nom) as seconde:
            assert seconde is False


@windows_only
def test_verrou_libere_apres_usage():
    nom = "Local\\SecDailyBrief-test-libere"
    with lock.instance_unique(nom) as premiere:
        assert premiere is True
    with lock.instance_unique(nom) as seconde:
        assert seconde is True

# --- Trousseau Linux : le secret ne passe pas par la ligne de commande ---------------------

def test_le_secret_passe_par_l_entree_standard(monkeypatch):
    """Un secret en argument serait lisible dans `ps` par tout le monde."""
    pytest.importorskip("fcntl")      # module Linux : ces tests ne valent que la-bas
    from secdailybrief.plateforme import linux

    appels = []

    class Resultat:
        returncode = 0
        stdout = b""

    def faux_run(commande, **options):
        appels.append((commande, options))
        return Resultat()

    monkeypatch.setattr(linux.subprocess, "run", faux_run)

    linux._secret_tool("store", "--label=SecDailyBrief", "service", "SecDailyBrief",
                       entree="s3cr3t")

    commande, options = appels[0]
    assert "s3cr3t" not in " ".join(commande)
    assert options["input"] == b"s3cr3t"


def test_store_du_trousseau_appelle_l_entree_standard(monkeypatch):
    """`value=` sur une fonction sans mot-cle levait un TypeError : CodeQL l'a releve."""
    pytest.importorskip("fcntl")      # module Linux : ces tests ne valent que la-bas
    from secdailybrief.plateforme import linux

    vus = {}

    def faux_secret_tool(*arguments, entree=None):
        vus["arguments"] = arguments
        vus["entree"] = entree

        class Resultat:
            returncode = 0
            stdout = b""

        return Resultat()

    monkeypatch.setattr(linux, "TROUSSEAU_DISPONIBLE", True)
    monkeypatch.setattr(linux, "_secret_tool", faux_secret_tool)

    assert linux.chiffrer("mon-secret") == b"secret-service"
    assert vus["arguments"][0] == "store"
    assert vus["entree"] == "mon-secret"


def test_sans_trousseau_le_secret_reste_dans_le_fichier(monkeypatch):
    pytest.importorskip("fcntl")      # module Linux : ces tests ne valent que la-bas
    from secdailybrief.plateforme import linux

    monkeypatch.setattr(linux, "TROUSSEAU_DISPONIBLE", False)

    assert linux.chiffrer("mon-secret") == b"mon-secret"
