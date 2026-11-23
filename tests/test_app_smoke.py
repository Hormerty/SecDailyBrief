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

from secdailybrief import app, paths, secrets

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


def test_le_consentement_conditionne_le_bouton(application):
    """Une case à cocher qui ne bloque rien ne demande rien."""
    application.page_consentement()
    assert application.bouton_consentement.instate(["disabled"])

    application.consentement.set(True)
    application._maj_bouton_consentement()
    assert application.bouton_consentement.instate(["!disabled"])

    application.consentement.set(False)
    application._maj_bouton_consentement()
    assert application.bouton_consentement.instate(["disabled"])


def test_page_stack_remplie_avec_les_defauts_du_moteur(application):
    application.page_stack()
    lignes = application.arbre.get_children()
    assert lignes, "la stack d'exemple doit être proposée"
    noms = [application.arbre.item(ligne, "text") for ligne in lignes]
    assert "Box" in noms


def test_fuseau_propose_dans_une_liste(application):
    """Un champ vide sans liste ne laisse aucun moyen de choisir."""
    application.page_planification()
    assert application.var_fuseau.get() == "Europe/Brussels"
    assert "Europe/Brussels" in application.fuseaux_proposes
    # Éditable : la liste complète fait six cents entrées, elle ne peut pas y être.
    assert str(application.combo_fuseau.cget("state")) != "readonly"


def test_ajout_d_un_produit_a_la_stack(application):
    application.page_stack()
    application.var_stack_nom.set("GitLab")
    application.var_stack_mots.set("gitlab, gitlab runner")
    application._stack_enregistrer()

    assert application.stack["GitLab"] == ["gitlab", "gitlab runner"]
    assert "GitLab" in [application.arbre.item(l, "text")
                        for l in application.arbre.get_children()]
    assert application.perimetre["stack"]["GitLab"] == ["gitlab", "gitlab runner"]


def test_suppression_d_un_produit(application):
    application.page_stack()
    avant = len(application.stack)
    premiere = application.arbre.get_children()[0]
    application.arbre.selection_set(premiere)
    application._stack_supprimer()

    assert len(application.stack) == avant - 1


def test_retour_a_la_stack_d_exemple(application):
    application.page_stack()
    application.var_stack_nom.set("Produit perso")
    application.var_stack_mots.set("produit perso")
    application._stack_enregistrer()
    assert "Produit perso" in application.stack

    application._stack_reinitialiser()
    assert "Produit perso" not in application.stack
    assert "Box" in application.stack


def test_terminer_enregistre_le_mot_de_passe_et_rafraichit_le_diagnostic(application, monkeypatch):
    """Le diagnostic lisait l'état en mémoire : il annonçait « aucun mot de passe » après
    l'avoir enregistré. C'est exactement le rapport qu'a reçu l'utilisateur."""
    monkeypatch.setattr(application, "_programmer", lambda: None)  # pas de tâche en test
    application.page_courriel()
    application.var_expediteur.set("bot@example.com")
    application.var_destinataire.set("bot@example.com")
    application.var_mot_de_passe.set("abcd efgh ijkl mnop")
    application._courriel_suivant()          # le chemin réel : « Suivant », sans test d'envoi
    application.page_planification()         # les champs de planification n'existent qu'ici
    application.var_heure.set("06:00")
    application.var_fenetre.set("27")
    application.var_fuseau.set("Europe/Brussels")

    application._terminer()

    assert secrets.charger_jetons(paths.chemin_secret())["smtp_password"] == \
        "abcd efgh ijkl mnop"
    assert application.jetons["smtp_password"] == "abcd efgh ijkl mnop"


def test_adresse_outlook_refusee(application):
    application.page_courriel()
    application.var_expediteur.set("quelquun@outlook.com")
    application.var_destinataire.set("quelquun@outlook.com")
    assert application._collecter_courriel() is False


def test_domaines_contactes_lus_depuis_le_moteur():
    domaines = app.domaines_contactes()
    assert "cert.cyber.gouv.fr" in domaines
    assert all(" " not in domaine for domaine in domaines)
