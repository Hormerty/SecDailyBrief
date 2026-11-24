"""Validation stricte du fichier de périmètre : nommer la faute, pas la subir au run."""
from __future__ import annotations

from secdailybrief import config


def test_un_perimetre_valide_ne_produit_aucun_probleme():
    valide = {
        "countries": {"BE": {"name": "Belgium", "flag": "🇧🇪", "keywords": ["belgium"]}},
        "stack": {"Box": ["box drive", "box cloud"]},
        "targets": ["microsoft exchange", "apache struts"],
    }

    assert config.valider_perimetre(valide) == []


def test_un_commentaire_est_tolere():
    assert config.valider_perimetre({"_commentaire": "note", "stack": {}}) == []


def test_une_section_inconnue_est_signalee():
    problemes = config.valider_perimetre({"stack": {}, "produits": ["box"]})

    assert any("produits" in probleme for probleme in problemes)


def test_une_stack_en_liste_est_signalee():
    problemes = config.valider_perimetre({"stack": ["box drive"]})

    assert any("stack" in probleme and "objet attendu" in probleme for probleme in problemes)


def test_une_stack_sans_mots_cles_est_signalee():
    problemes = config.valider_perimetre({"stack": {"Box": []}})

    assert any("stack.Box" in probleme for probleme in problemes)


def test_des_cibles_non_textuelles_sont_signalees():
    problemes = config.valider_perimetre({"targets": ["ok", 42]})

    assert len(problemes) == 1
    assert "targets[1]" in problemes[0]


def test_un_fichier_qui_n_est_pas_un_objet_est_refuse():
    assert config.valider_perimetre(["box"]) == ["le fichier doit contenir un objet JSON"]


def test_le_fichier_de_l_utilisateur_reel_passe_la_validation(tmp_path):
    """Le périmètre écrit par l'application doit évidemment être valide."""
    perimetre = {"countries": {}, "stack": {"Box": ["box drive"]}, "targets": ["struts"]}
    config.enregistrer_perimetre(tmp_path, perimetre)

    assert config.valider_perimetre(config.charger_perimetre(tmp_path)) == []
