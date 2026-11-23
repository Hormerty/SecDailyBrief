"""Test de fumée de l'interface : elle se construit, elle se parcourt, elle se ferme.

Ce n'est pas un test d'apparence — c'est un filet. Une faute de nom d'option, un widget
mal placé ou un rappel qui lève à la construction sont exactement ce qui casse une
interface sans qu'aucun test unitaire ne le voie.

Une seule fenêtre Tk est créée par test, jamais une à l'import puis une autre dans la
fixture : cette double initialisation casse Tcl, et le symptôme (« can't find a usable
init.tcl ») n'a rien à voir avec l'installation.
"""
from __future__ import annotations

import tkinter as tk

import pytest

from secdailybrief import app, paths

pied_attendu = "Developed by Hormerty · © 2026"


@pytest.fixture(scope="module")
def racine():
    """Une seule racine Tk pour tous les tests : la détruire et la recréer casse Tcl."""
    try:
        fenetre = tk.Tk()
    except tk.TclError as exc:      # runtime allégé, ou pas de session graphique
        pytest.skip(f"Tk indisponible : {exc}")
    fenetre.withdraw()
    yield fenetre
    fenetre.destroy()


@pytest.fixture
def application(racine, tmp_path, monkeypatch):
    monkeypatch.setenv(paths.VARIABLE_DONNEES, str(tmp_path))
    dossier = paths.s_assurer_dossier()
    # Les boîtes de dialogue sont modales : un test qui en ouvre une ne rend jamais la main.
    monkeypatch.setattr(app.messagebox, "showinfo", lambda *a, **k: "ok")
    monkeypatch.setattr(app.messagebox, "showerror", lambda *a, **k: "ok")
    monkeypatch.setattr(app.messagebox, "askyesno", lambda *a, **k: False)

    instance = app.Application(racine, dossier)
    try:
        yield instance
    finally:
        instance.corps.destroy()
        instance.pied.destroy()


def test_assistant_se_construit_et_le_pied_est_visible(application):
    assert application.pied.cget("text") == pied_attendu
    assert application.pied.winfo_manager() == "pack"
    # Empilé en bas, et avec une hauteur naturelle : dans pack(), le premier arrivé reçoit
    # sa place. Un widget peut exister, être packé, et n'avoir aucun pixel.
    assert application.pied.pack_info()["side"] == "bottom"
    assert application.pied.winfo_reqheight() > 10
    assert application.corps.pack_info()["side"] == "top"


def test_parcours_des_pages_ne_leve_pas(application):
    application.page_consentement()
    application.page_courriel()
    application.page_planification()
    application.afficher_panneau()


def test_page_stack_remplie_avec_les_defauts_du_moteur(application):
    application.page_stack()
    lignes = application.arbre.get_children()
    assert lignes, "la stack d'exemple doit être proposée"
    noms = [application.arbre.item(ligne, "text") for ligne in lignes]
    assert "Box" in noms


def test_adresse_outlook_refusee(application):
    application.page_courriel()
    application.var_expediteur.set("quelquun@outlook.com")
    application.var_destinataire.set("quelquun@outlook.com")
    assert application._collecter_courriel() is False


def test_domaines_contactes_lus_depuis_le_moteur():
    domaines = app.domaines_contactes()
    assert "cert.cyber.gouv.fr" in domaines
    assert all(" " not in domaine for domaine in domaines)
