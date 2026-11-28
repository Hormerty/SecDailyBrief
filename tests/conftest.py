"""Isolation des tests : aucun d'eux n'écrit dans le profil de l'utilisateur.

Sans ce garde-fou, un test qui traversait `main()` écrivait dans le vrai journal et dans le vrai
historique. Le symptôme était visible à l'écran : chaque exécution y apparaissait deux fois, une
fois « terminée » et une fois « en erreur » en 0,1 s, et le journal se remplissait de traces de
tests. Le défaut n'était pas dans l'application, il était dans l'absence de ce fichier.
"""
import pytest


@pytest.fixture(autouse=True)
def profil_isole(tmp_path, monkeypatch):
    """Chaque test travaille dans son propre dossier de données."""
    monkeypatch.setenv("SECDailyBrief_DATA", str(tmp_path / "profil"))
