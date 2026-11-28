"""Tests de l'historique : borné, tolérant aux fichiers abîmés, daté."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from secdailybrief import historique, paths


@pytest.fixture
def isole_donnees(tmp_path, monkeypatch):
    """Les tests écrivent dans un dossier temporaire, jamais dans le profil réel."""
    monkeypatch.setenv(paths.VARIABLE_DONNEES, str(tmp_path))
    return tmp_path


def test_une_execution_est_enregistree(isole_donnees):
    historique.enregistrer("ok", 12.34, "run")

    entrees = historique.charger()

    assert len(entrees) == 1
    assert entrees[0]["statut"] == "ok"
    assert entrees[0]["duree"] == 12.3
    assert entrees[0]["mode"] == "run"


def test_l_historique_est_borne(isole_donnees):
    # Des horodatages distincts : deux exécutions dans la même seconde sont désormais fusionnées,
    # parce qu'elles viennent du même lancement vu par deux processus.
    depart = datetime.now() - timedelta(days=3)
    for indice in range(historique.MAX_ENTREES + 10):
        historique.enregistrer("ok", indice, "run", maintenant=depart + timedelta(minutes=indice))

    assert len(historique.charger()) == historique.MAX_ENTREES


def test_les_entrees_recentes_excluent_les_anciennes(isole_donnees):
    maintenant = datetime.now()
    historique.enregistrer("ok", 1, "run", maintenant=maintenant - timedelta(days=10))
    historique.enregistrer("ok", 2, "run", maintenant=maintenant)

    recentes = historique.recentes(7, maintenant=maintenant)

    assert [entree["duree"] for entree in recentes] == [2]


def test_les_plus_recentes_viennent_en_premier(isole_donnees):
    maintenant = datetime.now()
    historique.enregistrer("ok", 1, "run", maintenant=maintenant - timedelta(days=1))
    historique.enregistrer("ok", 2, "run", maintenant=maintenant)

    assert [entree["duree"] for entree in historique.recentes(7, maintenant=maintenant)] \
        == [2, 1]


def test_un_fichier_abime_ne_leve_pas(isole_donnees):
    historique.chemin().write_text("{ceci n'est pas du json", encoding="utf-8")

    assert historique.charger() == []
    assert historique.recentes() == []


def test_une_entree_sans_date_est_ignoree(isole_donnees):
    historique.chemin().write_text('[{"statut": "ok"}]', encoding="utf-8")

    assert historique.charger() == [{"statut": "ok"}]
    assert historique.recentes() == []

# --- Historique attribuable, et certificats poses dans l'environnement ---------------------

def test_deux_executions_dans_la_meme_seconde_sont_fusionnees(isole_donnees):
    """Le planificateur et l'interface peuvent lancer la même exécution : une seule ligne."""
    moment = datetime.now()
    historique.enregistrer("ok", 0.1, "run", maintenant=moment, origine="interface")
    historique.enregistrer("erreur", 0.2, "run", maintenant=moment, origine="planificateur")

    entrees = historique.charger()

    assert len(entrees) == 1
    assert entrees[0]["statut"] == "erreur"      # le statut le plus grave l'emporte
    assert entrees[0]["duree"] == 0.2
    assert entrees[0]["origine"] == "planificateur"


def test_deux_modes_differents_ne_sont_pas_fusionnes(isole_donnees):
    moment = datetime.now()
    historique.enregistrer("ok", 1, "run", maintenant=moment)
    historique.enregistrer("ok", 1, "alerte", maintenant=moment)

    assert len(historique.charger()) == 2


def test_l_origine_est_conservee(isole_donnees):
    historique.enregistrer("ok", 1.5, "run", origine="interface")

    assert historique.charger()[-1]["origine"] == "interface"


def test_le_paquet_de_certificats_est_pose_dans_l_environnement(tmp_path):
    """Sans lui, une exécution mourait en 0,1 s sur « CA certificate bundle »."""
    import logging
    from pathlib import Path

    from secdailybrief import runner

    env = runner.environnement({"email_user": "a@b.c", "timezone": "Europe/Brussels"},
                               "motdepasse", Path("."), {}, )

    assert env["REQUESTS_CA_BUNDLE"] == env["SSL_CERT_FILE"]
    assert env["REQUESTS_CA_BUNDLE"].endswith("cacert.pem")
    assert "WEBHOOKS" not in env

# --- A15, A20 : historique borné, en-têtes du message de test -------------------------

def test_l_historique_couvre_une_semaine_meme_avec_les_alertes(isole_donnees):
    """Neuf passages par jour (le rapport plus huit alertes) font 63 entrées : 60 en tronquait une."""
    from datetime import datetime, timedelta

    from secdailybrief import historique

    depart = datetime.now() - timedelta(days=7)
    for indice in range(7 * 9):
        historique.enregistrer("ok", 1.0, "run", maintenant=depart + timedelta(hours=indice))

    assert len(historique.charger()) == 63          # rien n'a été perdu
    assert historique.MAX_ENTREES >= 7 * 9
