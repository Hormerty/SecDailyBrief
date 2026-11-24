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
    for indice in range(historique.MAX_ENTREES + 10):
        historique.enregistrer("ok", indice, "run")

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
