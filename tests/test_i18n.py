"""Tests des textes : aucune langue ne doit être proposée avec des trous."""
from __future__ import annotations

from secdailybrief import i18n


def test_toutes_les_langues_ont_les_memes_cles():
    reference = set(i18n.TEXTES["en"])
    for code, dictionnaire in i18n.TEXTES.items():
        manquantes = reference - set(dictionnaire)
        assert not manquantes, f"{code} : clés manquantes {sorted(manquantes)}"


def test_langues_proposees_triees_et_completes():
    assert i18n.langues_proposees() == sorted(i18n.TEXTES)
    assert "fr" in i18n.langues_proposees() and "en" in i18n.langues_proposees()


def test_langue_inconnue_retombe_sur_l_anglais():
    assert i18n.apparier_langue_systeme("de-DE") == "en"
    assert i18n.apparier_langue_systeme(None) == "en"


def test_langue_systeme_appariee():
    assert i18n.apparier_langue_systeme("fr-BE") == "fr"
    assert i18n.apparier_langue_systeme("en-US") == "en"


def test_cle_manquante_completee_par_l_anglais():
    partiel = dict(i18n.TEXTES["fr"])
    textes = i18n.textes("fr")
    assert textes["wizard.suivant"] == partiel["wizard.suivant"]
    assert set(textes) >= set(i18n.TEXTES["en"])


def test_mention_legale_jamais_traduite():
    for code in i18n.langues_proposees():
        assert i18n.textes(code)["app.pied"] == "Developed by Hormerty · © 2026"
