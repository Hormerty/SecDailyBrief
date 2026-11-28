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

from secdailybrief import app, config, historique, paths, secrets

pied_attendu = "Developed by Hormerty · © 2026"


@pytest.fixture(scope="module")
def racine():
    """Une seule racine Tk pour tous les tests : la détruire et la recréer casse Tcl."""
    # Initialisé avant le try : CodeQL ne sait pas que pytest.skip lève, et signalait la
    # variable comme peut-être non initialisée à la ligne suivante.
    fenetre = None
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
    # La zone vient de la détection, plus d'une constante : la liste doit donc la contenir.
    assert application.var_fuseau.get() == application.brouillon["timezone"]
    assert application.var_fuseau.get() in application.fuseaux_proposes
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


def test_pendant_un_lancement_les_boutons_sont_desactives(application, monkeypatch):
    """Un clic sur « Lancer maintenant » doit dire qu'il travaille, et fermer les autres portes."""
    import threading
    import time as _time

    porte = threading.Event()

    def bloque(*arguments, **options):
        porte.wait(3)
        return app.runner.Resultat("ok", 0, 0.1, [])

    monkeypatch.setattr(app.runner, "executer", bloque)
    application.afficher_panneau()
    application.mot_de_passe = "motdepasse"

    application._lancer("run")

    assert application._en_cours is True
    assert all(bouton.instate(["disabled"]) for bouton in application.boutons_action)
    assert application.var_activite.get() == application._texte("panneau.en_cours")

    porte.set()
    for _ in range(100):
        application.racine.update()
        if not application._en_cours:
            break
        _time.sleep(0.02)

    assert application._en_cours is False
    assert all(bouton.instate(["!disabled"]) for bouton in application.boutons_action)


def test_la_tache_planifiee_lance_l_application_pas_le_moteur(application, monkeypatch):
    """`--moteur` court-circuite pré-vol, verrou, journal et dossier de travail : la tâche
    doit appeler `--run`. La première tâche créée appelait `--moteur`."""
    xmls = []
    monkeypatch.setattr(app.schedule, "installer", lambda xml, nom=None: xmls.append(xml))
    application.page_planification()
    application.var_heure.set("06:00")
    application.var_fenetre.set("27")
    application.var_fuseau.set("Europe/Brussels")

    application._programmer()

    assert xmls, "aucune tâche n'a été installée"
    # En développement la commande est « python -m secdailybrief --run », dans l'exe figé
    # c'est « SecDailyBrief.exe --run » : l'invariant est --run, jamais --moteur.
    assert "--run" in xmls[0]
    assert "--moteur" not in xmls[0]


def test_le_consentement_est_memorise_et_ne_bloque_plus_au_retour(application, monkeypatch):
    """Revenir sur la page langue pour la changer ne doit pas redemander le consentement."""
    monkeypatch.setattr(application, "_programmer", lambda: None)
    application.page_courriel()
    application.var_expediteur.set("bot@example.com")
    application.var_destinataire.set("bot@example.com")
    application.var_mot_de_passe.set("abcd efgh ijkl mnop")
    application._courriel_suivant()
    application.page_planification()
    application.var_heure.set("06:00")
    application.var_fenetre.set("27")
    application.var_fuseau.set("Europe/Brussels")
    application._terminer()

    enregistre = config.charger(application.dossier)
    assert enregistre["consentement"] is True

    # Au retour sur la page, l'état enregistré pré-remplit la case : « Suivant » reste
    # disponible, donc le chemin vers la page langue est praticable.
    application.brouillon["consentement"] = enregistre["consentement"]
    application.page_consentement()
    assert application.consentement.get() is True
    assert application.bouton_consentement.instate(["!disabled"])


def test_changer_de_langue_change_les_boutons_du_panneau(application):
    """Le panneau est reconstruit à chaque affichage : les libellés doivent suivre."""
    application.page_courriel()
    application._basculer_langue("nl")
    application.afficher_panneau()

    assert application._texte("panneau.lancer") == "Nu uitvoeren"
    libelles = []

    def parcourir(widget):
        for enfant in widget.winfo_children():
            try:
                libelles.append(str(enfant.cget("text")))
            except Exception:       # noqa: BLE001 - tous les widgets n'ont pas de texte
                pass
            parcourir(enfant)

    parcourir(application.corps)
    assert "Nu uitvoeren" in libelles
    assert "Lancer maintenant" not in libelles


def test_les_trois_langues_traduisent_les_memes_boutons(application):
    for code, attendu in (("fr", "Lancer maintenant"), ("en", "Run now"),
                          ("nl", "Nu uitvoeren")):
        application._basculer_langue(code)
        assert application._texte("panneau.lancer") == attendu


def test_la_fenetre_d_historique_liste_les_executions(application):
    historique.enregistrer("ok", 42.0, "run")
    application.afficher_panneau()

    application._ouvrir_historique()

    fenetres = [w for w in application.racine.winfo_children() if isinstance(w, tk.Toplevel)]
    assert fenetres, "aucune fenêtre d'historique ouverte"
    fenetres[-1].destroy()


def test_un_perimetre_fautif_est_signale_et_restaure(application, monkeypatch):
    """Le fichier fautif doit être nommé à l'ouverture, pas découvert au run."""
    mauvais = config.chemin_perimetre(application.dossier)
    mauvais.write_text('{"stack": ["box drive"]}', encoding="utf-8")
    monkeypatch.setattr(app.messagebox, "askyesno", lambda *a, **k: True)

    application._perimetre_en_attente = ["stack : objet attendu"]
    application._signaler_perimetre()

    assert config.charger_perimetre(application.dossier) == {}
    assert (mauvais.with_name(mauvais.name + ".invalide")).exists()


def test_des_reglages_fautifs_sont_signales_sans_effacer_l_adresse(application, monkeypatch):
    """Corriger, pas réinitialiser : effacer les réglages effacerait l'adresse."""
    monkeypatch.setattr(app.messagebox, "askyesno", lambda *a, **k: False)
    application.reglages["email_user"] = "quelquun@example.com"
    avant = dict(application.reglages)
    application._reglages_en_attente = ["heure : format attendu HH:MM"]

    application._signaler_reglages()

    assert application._reglages_en_attente == []
    assert application.reglages == avant, "les réglages ne doivent pas être réinitialisés"


def test_le_bouton_de_mise_a_jour_annonce_une_version_plus_recente(application, monkeypatch):
    """La requête part hors du fil UI, puis le résultat revient par le fil principal."""
    import time as _time

    monkeypatch.setattr(app.updates, "derniere_release",
                        lambda *a, **k: {"tag": "v9.9.9", "empreintes": {}})
    vus = []
    monkeypatch.setattr(application, "_afficher_maj",
                        lambda publiee, empreintes: vus.append((publiee, empreintes)))
    application.afficher_panneau()
    statut_avant = application.var_statut.get()

    application._verifier_maj()
    for _ in range(200):
        application.racine.update()
        if not application._maj_en_cours:
            break
        _time.sleep(0.02)

    assert vus, "aucune fenêtre annonçant la nouvelle version"
    assert vus[0][0] == "v9.9.9"
    assert application.var_statut.get() == statut_avant, "la ligne d'état doit être restaurée"


def test_le_panneau_donne_acces_aux_reglages(application):
    """Sans cette porte, une configuration déjà enregistrée n'était plus modifiable."""
    application.afficher_panneau()
    textes = []

    def parcourir(widget):
        for enfant in widget.winfo_children():
            try:
                textes.append(str(enfant.cget("text")))
            except Exception:       # noqa: BLE001 - tous les widgets n'ont pas de texte
                pass
            parcourir(enfant)

    parcourir(application.corps)
    assert application._texte("panneau.reglages") in textes


def test_adresse_outlook_refusee(application):
    application.page_courriel()
    application.var_expediteur.set("quelquun@outlook.com")
    application.var_destinataire.set("quelquun@outlook.com")
    assert application._collecter_courriel() is False


def test_domaines_contactes_lus_depuis_le_moteur():
    domaines = app.domaines_contactes()
    assert "cert.cyber.gouv.fr" in domaines
    assert all(" " not in domaine for domaine in domaines)

# --- Navigation : on ne reste jamais prisonnier d'un écran ---------------------------------

def test_precedent_depuis_reglages_revient_au_panneau(application, monkeypatch):
    """Ouvert par « Réglages », « Précédent » remontait vers le consentement puis la langue :
    impossible de revenir au panneau, et les canaux d'alerte inatteignables."""
    application.reglages["email_user"] = "bot@example.com"
    appels = []
    monkeypatch.setattr(application, "afficher_panneau", lambda: appels.append("panneau"))
    monkeypatch.setattr(application, "page_consentement", lambda: appels.append("consentement"))

    application._precedent_courriel()

    assert appels == ["panneau"]


def test_precedent_au_premier_lancement_remonte_l_assistant(application, monkeypatch):
    """Sans configuration enregistrée, il n'y a pas de panneau où revenir."""
    application.reglages.pop("email_user", None)
    appels = []
    monkeypatch.setattr(application, "afficher_panneau", lambda: appels.append("panneau"))
    monkeypatch.setattr(application, "page_consentement", lambda: appels.append("consentement"))

    application._precedent_courriel()

    assert appels == ["consentement"]


def test_le_panneau_ouvre_les_canaux_en_un_clic(application):
    """Les canaux vivaient au bout de l'assistant, sans porte une fois la configuration faite."""
    application.reglages["email_user"] = "bot@example.com"
    application.afficher_panneau()

    application.page_planification()                  # ce que fait le bouton « Alertes »

    for nom in ("var_mail", "var_slack_on", "var_discord_on", "var_telegram_on",
                "var_discord", "var_telegram_token"):
        assert hasattr(application, nom), nom


def test_revenir_des_canaux_ne_perd_pas_les_webhooks(application):
    """« Précédent » puis « Suivant » vidait l'adresse Discord : elle était relue du fichier
    de secrets, qui n'avait pas encore été écrit."""
    application.reglages["email_user"] = "bot@example.com"
    application.page_planification()
    application.var_discord.set("https://discord.com/api/webhooks/123/abc")
    application.var_discord_on.set(True)
    application.var_telegram_token.set("123456:jeton")
    application.var_telegram_chat.set("-100999")

    application._precedent_planification()
    application.page_planification()

    assert application.var_discord.get() == "https://discord.com/api/webhooks/123/abc"
    assert application.var_discord_on.get() is True
    assert application.var_telegram_token.get() == "123456:jeton"
    assert application.var_telegram_chat.get() == "-100999"

# --- Fenêtre « À propos » ----------------------------------------------------------------

def test_about_affiche_la_version_du_paquet(application):
    """La fenêtre annonçait « 1.0.0 » en dur, six versions durant, pendant que le panneau et
    le badge des versions disaient autre chose."""
    import secdailybrief

    lignes = application._lignes_about()

    assert lignes[0] == f"SecDailyBrief {secdailybrief.__version__}"
    assert "1.0.0" not in "\n".join(lignes)


def test_about_suit_une_version_differente(application, monkeypatch):
    """La vérification porte sur le paquet, pas sur la valeur du jour."""
    monkeypatch.setattr(app, "version_actuelle", "9.9.9")

    assert application._lignes_about()[0] == "SecDailyBrief 9.9.9"

# --- Aide des canaux : le « ? » a côté de Discord, Slack et Telegram ----------------------

def test_chaque_canal_a_son_aide(application):
    """Les champs ne disaient pas quoi y coller : un « ? » par canal, qui mène à sa section."""
    application.reglages["email_user"] = "bot@example.com"
    application.page_planification()

    assert set(application.aides_canaux) == {"slack", "discord", "telegram"}
    for ancre, aide in application.aides_canaux.items():
        assert application._url_aide(ancre).endswith(f"docs/ALERTES.md#{ancre}")
        # Le « ? » est dans la troisieme colonne, a droite du champ.
        assert aide.grid_info()["column"] == 2


def test_l_aide_survolee_existe_dans_les_neuf_langues():
    """Le test de parité verifie la presence des cles ; celui-ci verifie qu'elles disent
    quelque chose, et que la traduction n'est pas restee vide."""
    from secdailybrief import i18n

    for code in i18n.TEXTES:
        textes = i18n.textes(code)
        for cle in ("alertes.aide.discord", "alertes.aide.slack", "alertes.aide.telegram"):
            assert textes[cle].strip(), f"{code} : {cle} vide"

def test_l_infobulle_indique_qu_on_peut_cliquer(application, monkeypatch):
    """Le survol dit quoi coller ; il doit aussi dire qu'un clic mène plus loin."""
    textes = []
    monkeypatch.setattr(application, "_info_bulle",
                        lambda widget, texte: textes.append(texte))
    application.reglages["email_user"] = "bot@example.com"

    application.page_planification()

    assert len(textes) == 3
    for texte in textes:
        assert application._texte("alertes.aide.clic") in texte
        assert "\n" in texte

def test_la_fenetre_de_mise_a_jour_montre_l_empreinte(application):
    """Une boîte de dialogue ne laisse pas copier son texte : l'empreinte est dans un champ."""
    attendu = app.updates.nom_archive("9.9.9", portable=app.paths.est_portable())

    application._afficher_maj("v9.9.9", {attendu: "abc123def456"})

    champs = []

    def parcourir(widget):
        for enfant in widget.winfo_children():
            if enfant.winfo_class() in ("TEntry", "Entry"):
                champs.append(enfant.get())
            parcourir(enfant)

    parcourir(application.racine)
    assert "abc123def456" in champs

    # On referme la fenetre ouverte par le test : une fenetre par test, pas une de plus.
    for enfant in application.racine.winfo_children():
        if isinstance(enfant, tk.Toplevel):
            enfant.destroy()


def test_la_fenetre_de_mise_a_jour_sans_empreinte_le_dit(application):
    """Si l'empreinte manque, on renvoie vers SHA256SUMS plutot que d'afficher un champ vide."""
    application._afficher_maj("v9.9.9", {})

    textes = []

    def parcourir(widget):
        for enfant in widget.winfo_children():
            try:
                textes.append(str(enfant.cget("text")))
            except tk.TclError:
                pass
            parcourir(enfant)

    parcourir(application.racine)
    assert any("SHA256SUMS" in texte for texte in textes)

    for enfant in application.racine.winfo_children():
        if isinstance(enfant, tk.Toplevel):
            enfant.destroy()

def test_about_lit_le_commit_du_moteur_epingle(application):
    """Le binaire figé posait vendor/ sous _internal : la fenêtre affichait « Engine: ? »."""
    import json

    verrou = json.loads((app.engine.dossier() / "engine.json").read_text(encoding="utf-8"))

    lignes = application._lignes_about()

    assert verrou["commit"] in lignes[1]
    assert "?" not in lignes[1]


def test_about_efface_la_ligne_engine_si_le_verrou_manque(application, monkeypatch,
                                                      tmp_path):
    """Une ligne qui annonce « inconnu » est un defaut deguise : elle disparait."""
    monkeypatch.setattr(app.engine, "dossier", lambda: tmp_path)

    lignes = application._lignes_about()

    assert lignes[0].startswith("SecDailyBrief ")
    assert not any(application._texte("about.moteur") in ligne for ligne in lignes)
    assert "?" not in "".join(lignes)

def test_la_fenetre_about_n_a_pas_de_libelle_anglais_en_francais():
    """L'interface francaise affichait « About », « Engine », « License », « Repository » :
    le titre et les libelles n'avaient jamais ete traduits."""
    from secdailybrief import i18n

    fr = i18n.textes("fr")
    en = i18n.textes("en")

    for cle in ("about.titre", "about.moteur", "about.licence", "about.depot"):
        assert fr[cle] != en[cle], f"{cle} n'est pas traduit"


def test_une_erreur_du_fil_de_travail_debloque_la_fenetre(application, monkeypatch):
    """Sans cela, « Rapport en cours… » tournait indéfiniment, boutons désactivés."""
    vues = []
    monkeypatch.setattr(application, "_signaler_erreur_travail", vues.append)
    suite_appelee = []
    # monkeypatch, et non affectation directe : sinon la racine reste modifiee pour
    # tous les tests suivants, et leurs rappels after() deviennent recursifs.
    monkeypatch.setattr(application.racine, "after", lambda delai, rappel: rappel())

    def travail():
        raise RuntimeError("panne simulee")

    application._en_arriere_plan(travail, suite_appelee.append, delai=1)

    for _ in range(50):                 # le fil de travail est asynchrone
        if vues:
            break
        import time

        time.sleep(0.02)

    assert vues and isinstance(vues[0], RuntimeError)
    assert not suite_appelee            # le résultat n'est jamais utilisé quand il n'y en a pas


def test_le_mode_preview_n_exige_pas_de_mot_de_passe():
    """L'interface s'en passait, la ligne de commande non : même règle pour les deux."""
    from secdailybrief import runner

    assert runner.exige_mot_de_passe("preview") is False
    assert runner.exige_mot_de_passe("sources") is False
    assert runner.exige_mot_de_passe("run") is True
    assert runner.exige_mot_de_passe("alerte") is True


def test_les_erreurs_de_reglages_sont_affichees_en_clair(application):
    """« courriel.expediteur » au lieu d'« Adresse d'envoi » : illisible au moment où l'on est bloqué."""
    from secdailybrief import config

    problemes = config.valider({})
    libelles = application._libelles(problemes)

    assert "courriel.expediteur" not in libelles
    assert "Adresse d'envoi" in libelles
    assert len(libelles) == len(problemes)


def test_les_phrases_du_perimetre_traversent_sans_etre_traduites(application):
    """valider_perimetre() renvoie des phrases, pas des clés : elles doivent rester intactes."""
    phrase = "le fichier doit contenir un objet JSON"

    assert application._libelles([phrase]) == [phrase]


def test_le_test_d_envoi_ne_bloque_pas_le_fil_de_l_interface(application, monkeypatch):
    """Vingt secondes sans fenêtre, c'est Windows qui écrit « Ne répond pas » au bout de cinq."""
    from secdailybrief import app, mail

    application.page_courriel()          # la page construit var_mot_de_passe
    application.var_mot_de_passe.set("motdepasse")
    application._collecter_courriel = lambda: True
    application._synchroniser_adresses = lambda: None
    ordre = []

    def lent(config, mot_de_passe):
        ordre.append("debut")
        import time

        time.sleep(0.3)                     # simule la connexion SMTP
        ordre.append("fin")

    monkeypatch.setattr(mail, "tester_envoi", lent)

    application._tester_envoi()

    # Le libellé « en cours » est posé avant l'appel, et le fil UI a déjà rendu la main.
    assert application.var_test.get() in (
        application._texte("courriel.test.encours"),
        application._texte("courriel.test.ok"),
    )

    for _ in range(200):
        application.racine.update()      # laisse Tk executer les rappels after()
        if application.var_test.get() == application._texte("courriel.test.ok"):
            break
        import time

        time.sleep(0.01)

    assert ordre == ["debut", "fin"]
    assert application.var_test.get() == application._texte("courriel.test.ok")
    assert application.mot_de_passe == "motdepasse"


def test_un_test_d_envoi_rate_affiche_l_echec(application, monkeypatch):
    from secdailybrief import mail

    application.page_courriel()          # la page construit var_mot_de_passe
    application.var_mot_de_passe.set("motdepasse")
    application._collecter_courriel = lambda: True
    application._synchroniser_adresses = lambda: None

    def echoue(config, mot_de_passe):
        raise OSError("SMTP refuse")

    monkeypatch.setattr(mail, "tester_envoi", echoue)

    application._tester_envoi()

    import time

    for _ in range(200):
        application.racine.update()
        if application.var_test.get() == application._texte("courriel.test.echec"):
            break
        time.sleep(0.01)

    assert application.var_test.get() == application._texte("courriel.test.echec")
