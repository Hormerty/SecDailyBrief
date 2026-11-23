"""Interface graphique : assistant de premier lancement et panneau de contrôle.

Choix assumés pour cette version :

* **thème natif ttk uniquement**, clair — un mode sombre serait un thème complet à
  maintenir, et il n'apporte rien à un outil qu'on ouvre une fois par jour ;
* **le pied de fenêtre ne se traduit pas** : « Developed by Hormerty · © 2026 » reste en
  anglais et reste visible en permanence ;
* **aucune action longue sur le fil de l'interface** : le moteur tourne dans un fil, et le
  panneau ne se fige pas pendant une collecte de quatre minutes.
"""
from __future__ import annotations

import locale
import os
import re
import threading
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from . import config as configuration
from . import __version__ as version_actuelle
from . import engine, i18n, logging_setup, mail, paths, runner, schedule, secrets

TAILLE_MIN = (760, 540)
URL_MOT_DE_PASSE = "https://myaccount.google.com/apppasswords"
URL_DEPOT = "https://github.com/Hormerty/Sec_Daily_report-"
NBSP = "\u00a0"

# Raccourcis proposés dans la liste des fuseaux. La liste complète fait six cents entrées :
# un menu déroulant de cette taille est inutilisable. Le champ reste éditable, donc toute
# zone IANA valide est acceptée — la liste est un confort, pas une limite.
FUSEAUX_COURANTS = (
    "Europe/Brussels", "Europe/Paris", "Europe/London", "Europe/Berlin", "Europe/Madrid",
    "Europe/Rome", "Europe/Amsterdam", "Europe/Luxembourg", "Europe/Zurich", "Europe/Vienna",
    "Europe/Lisbon", "Europe/Warsaw", "Europe/Prague", "Europe/Stockholm",
    "Europe/Helsinki", "Europe/Athens", "Europe/Dublin", "Europe/Bucharest",
    "America/New_York", "America/Chicago", "America/Denver", "America/Los_Angeles",
    "America/Sao_Paulo", "Africa/Casablanca", "Africa/Johannesburg", "Asia/Dubai",
    "Asia/Kolkata", "Asia/Singapore", "Asia/Tokyo", "Australia/Sydney", "Pacific/Auckland",
    "UTC",
)


def domaines_contactes() -> list[str]:
    """Domaines réellement présents dans le moteur épinglé, lus depuis le fichier.

    Lire le source plutôt qu'importer le module : c'est instantané, et l'écran de
    consentement s'ouvre même si une dépendance du moteur manque.
    """
    source = engine.dossier() / "veille.py"
    if not source.exists():
        return []
    texte = source.read_text(encoding="utf-8", errors="replace")
    trouves = re.findall(r"https?://([^/\"'\s:]+)", texte)
    return sorted({domaine.lower() for domaine in trouves})


def langue_du_systeme() -> str | None:
    try:
        return locale.getlocale()[0]
    except (TypeError, ValueError):     # environnement sans locale configurée
        return None


class Application:
    """Une fenêtre, deux visages : l'assistant au premier lancement, le panneau ensuite."""

    def __init__(self, racine: tk.Tk, dossier: Path) -> None:
        self.racine = racine
        self.dossier = dossier
        self.reglages = configuration.charger(dossier)
        self.jetons = secrets.charger_jetons(paths.chemin_secret())
        self.perimetre = configuration.charger_perimetre(dossier)

        self.langue = self.reglages.get("langue") or i18n.apparier_langue_systeme(
            langue_du_systeme())
        self.textes = i18n.textes(self.langue)
        self.mot_de_passe = self.jetons.get("smtp_password", "")
        self.brouillon = dict(self.reglages)
        self.taille = int(self.reglages.get("taille_texte") or 10)
        self._maj_verifiee = False

        self.racine.title(self.textes["app.titre"])
        self.racine.minsize(*TAILLE_MIN)
        self.racine.protocol("WM_DELETE_WINDOW", self.racine.destroy)
        self.racine.bind("<Escape>", lambda _event: self.racine.destroy())
        self._appliquer_taille(self.taille)

        # Le pied est empilé AVANT la zone centrale : dans pack(), le premier arrivé reçoit
        # sa place. Empilé après, il se retrouve avec zéro pixel quand le centre s'étend —
        # et la mention « Developed by Hormerty » disparaît, ce qui est exactement ce
        # qu'elle ne doit jamais faire.
        self.pied = ttk.Label(self.racine, text=self.textes["app.pied"], anchor="w",
                              padding=(12, 6), relief="groove")
        self.pied.pack(side="bottom", fill="x")

        self.corps = ttk.Frame(self.racine, padding=16)
        self.corps.pack(side="top", fill="both", expand=True)

        if self.reglages.get("email_user"):
            self.afficher_panneau()
        else:
            self.page_langue()

        # Pour les captures d'écran et la documentation : ouvrir directement une page.
        # Sans cette variable, rien ne change pour un utilisateur.
        page = os.environ.get("SECDailyBrief_PAGE")
        if page and hasattr(self, f"page_{page}"):
            getattr(self, f"page_{page}")()

    # --- utilitaires -------------------------------------------------------
    def _titre(self, base: int) -> tuple[str, int, str]:
        """Taille d'un titre, relative à la taille de texte choisie par l'utilisateur."""
        return ("Segoe UI", base + self.taille - 10, "bold")

    def _appliquer_taille(self, taille: int) -> None:
        """Agrandit toute l'interface, pas seulement les titres.

        ttk lit ses polices dans des polices nommées de Tk : les redimensionner est le seul
        moyen d'agir sur chaque widget à la fois, y compris ceux qui n'existent pas encore.
        """
        self.taille = taille
        for nom in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont",
                    "TkCaptionFont", "TkSmallCaptionFont", "TkTooltipFont"):
            try:
                tkfont.nametofont(nom).configure(size=taille)
            except tk.TclError:     # police absente de cette installation
                continue

    def _vider(self) -> ttk.Frame:
        for enfant in self.corps.winfo_children():
            enfant.destroy()
        return ttk.Frame(self.corps)

    def _texte(self, cle: str) -> str:
        return self.textes.get(cle, cle)

    def _basculer_langue(self, code: str) -> None:
        self.langue = code
        self.textes = i18n.textes(code)
        self.reglages["langue"] = code
        self.pied.configure(text=self._texte("app.pied"))

    # --- assistant ---------------------------------------------------------
    def page_langue(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        ttk.Label(page, text=self._texte("wizard.bienvenue"),
                  font=self._titre(16)).pack(anchor="w")
        ttk.Label(page, text=self._texte("wizard.intro"), wraplength=680,
                  justify="left").pack(anchor="w", pady=(8, 16))
        ttk.Label(page, text=self._texte("wizard.langue")).pack(anchor="w")

        variable = tk.StringVar(value=self.langue)
        libelles = {code: code.upper() for code in i18n.langues_proposees()}
        choix = ttk.Combobox(page, values=list(libelles.values()), state="readonly", width=8)
        choix.set(libelles.get(self.langue, "EN"))
        choix.pack(anchor="w", pady=4)
        choix.bind("<<ComboboxSelected>>", lambda _e: self._choisir_langue(
            choix.get(), libelles, variable))

        barre = ttk.Frame(page)
        barre.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(barre, text=self._texte("wizard.suivant"),
                   command=self.page_consentement).pack(side="right")

    def _choisir_langue(self, valeur: str, libelles: dict[str, str], variable) -> None:
        code = next((c for c, libelle in libelles.items() if libelle == valeur), "en")
        self._basculer_langue(code)
        self.page_langue()

    def page_consentement(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        ttk.Label(page, text=self._texte("consent.titre"),
                  font=self._titre(14)).pack(anchor="w")
        ttk.Label(page, text=self._texte("consent.texte"), wraplength=690,
                  justify="left").pack(anchor="w", pady=(8, 8))
        ttk.Label(page, text=self._texte("consent.pause"), wraplength=690,
                  justify="left").pack(anchor="w", pady=(0, 12))

        domaines = domaines_contactes()
        cadre = ttk.LabelFrame(page, text=f"{self._texte('consent.domaines')} "
                                          f"({len(domaines)})", padding=8)
        cadre.pack(fill="both", expand=True)
        liste = tk.Listbox(cadre, height=8, activestyle="none")
        for domaine in domaines:
            liste.insert("end", domaine)
        liste.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(cadre, orient="vertical", command=liste.yview).pack(side="right",
                                                                         fill="y")

        self.consentement = tk.BooleanVar(value=False)
        ttk.Checkbutton(page, text=self._texte("consent.accepte"),
                        variable=self.consentement,
                        command=self._maj_bouton_consentement).pack(anchor="w", pady=(8, 0))

        barre = ttk.Frame(page)
        barre.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(barre, text=self._texte("wizard.precedent"),
                   command=self.page_langue).pack(side="left")
        # Désactivé tant que la case n'est pas cochée : une case qui ne conditionne rien
        # ne demande rien, et laisserait croire à un consentement qui n'a pas eu lieu.
        self.bouton_consentement = ttk.Button(barre, text=self._texte("wizard.suivant"),
                                              command=self.page_courriel, state="disabled")
        self.bouton_consentement.pack(side="right")

    def _maj_bouton_consentement(self) -> None:
        self.bouton_consentement.configure(
            state="normal" if self.consentement.get() else "disabled")

    def page_courriel(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        ttk.Label(page, text=self._texte("courriel.titre"),
                  font=self._titre(14)).pack(anchor="w")

        cadre = ttk.Frame(page)
        cadre.pack(fill="x", pady=(12, 0))
        cadre.columnconfigure(1, weight=1)

        self.var_expediteur = tk.StringVar(value=self.brouillon.get("email_user", ""))
        self.var_destinataire = tk.StringVar(
            value=self.brouillon.get("recipient_email") or self.brouillon.get("email_user", ""))
        self.var_meme = tk.BooleanVar(value=True)
        self.var_mot_de_passe = tk.StringVar(value="")

        ttk.Label(cadre, text=self._texte("courriel.expediteur")).grid(row=0, column=0,
                                                                      sticky="w", pady=4)
        ttk.Entry(cadre, textvariable=self.var_expediteur).grid(row=0, column=1, sticky="ew")

        ttk.Label(cadre, text=self._texte("courriel.destinataire")).grid(row=1, column=0,
                                                                        sticky="w", pady=4)
        ttk.Entry(cadre, textvariable=self.var_destinataire).grid(row=1, column=1, sticky="ew")
        ttk.Checkbutton(cadre, text=self._texte("courriel.meme"), variable=self.var_meme,
                        command=self._synchroniser_adresses).grid(row=2, column=1, sticky="w")

        ttk.Label(cadre, text=self._texte("courriel.motdepasse")).grid(row=3, column=0,
                                                                      sticky="w", pady=(12, 4))
        ttk.Entry(cadre, textvariable=self.var_mot_de_passe, show="•").grid(
            row=3, column=1, sticky="ew")

        aide = ttk.Frame(page)
        aide.pack(fill="x", pady=(10, 0))
        ttk.Label(aide, text=self._texte("courriel.aide"), wraplength=560,
                  justify="left").pack(side="left")
        ttk.Button(aide, text=self._texte("courriel.lien"),
                   command=lambda: webbrowser.open(URL_MOT_DE_PASSE)).pack(side="right")

        self.var_test = tk.StringVar(value="")
        ttk.Label(page, textvariable=self.var_test, foreground="#1b5e20").pack(anchor="w",
                                                                               pady=(8, 0))

        barre = ttk.Frame(page)
        barre.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(barre, text=self._texte("wizard.precedent"),
                   command=self.page_consentement).pack(side="left")
        ttk.Button(barre, text=self._texte("courriel.tester"),
                   command=self._tester_envoi).pack(side="left", padx=8)
        ttk.Button(barre, text=self._texte("wizard.suivant"),
                   command=self._courriel_suivant).pack(side="right")

    def _courriel_suivant(self) -> None:
        """« Suivant » enregistre ce qui est saisi avant de changer de page.

        Sans cela, remplir le formulaire sans cliquer « Tester l'envoi » perdait l'adresse
        et le mot de passe : la page suivante était atteinte, mais la configuration ne
        contenait rien. Le test d'envoi reste facultatif — c'est une vérification, pas une
        condition.
        """
        if self._collecter_courriel():
            self.page_stack()

    def _synchroniser_adresses(self) -> None:
        if self.var_meme.get():
            self.var_destinataire.set(self.var_expediteur.get())

    def _collecter_courriel(self) -> bool:
        expediteur = self.var_expediteur.get().strip()
        destinataire = self.var_destinataire.get().strip() or expediteur
        self.brouillon["email_user"] = expediteur
        self.brouillon["recipient_email"] = destinataire
        # Le mot de passe saisi est mémorisé même sans test : exiger un test pour pouvoir
        # terminer transformerait une vérification facultative en obligation déguisée.
        if self.var_mot_de_passe.get():
            self.mot_de_passe = self.var_mot_de_passe.get()
        if expediteur.lower().endswith(("@outlook.com", "@hotmail.com", "@live.com",
                                        "@outlook.fr", "@hotmail.fr")):
            # Une information, pas une erreur : rien n'est cassé, la fonctionnalité manque.
            messagebox.showinfo(self._texte("commun.information"),
                                self._texte("courriel.outlook"))
            return False
        problemes = configuration.valider(self.brouillon)
        if "courriel.expediteur" in problemes or "courriel.destinataire" in problemes:
            messagebox.showerror(self._texte("commun.erreur"),
                                 self._texte("courriel.expediteur"))
            return False
        return True

    def _tester_envoi(self) -> None:
        self._synchroniser_adresses()
        if not self._collecter_courriel():
            return
        mot_de_passe = self.var_mot_de_passe.get() or self.mot_de_passe
        if not mot_de_passe:
            self.var_test.set(self._texte("courriel.test.echec"))
            return
        self.var_test.set("…")
        self.racine.update_idletasks()
        try:
            mail.tester_envoi(self.brouillon, mot_de_passe)
        except Exception:                       # noqa: BLE001 - tout échec se dit à l'écran
            self.var_test.set(self._texte("courriel.test.echec"))
            return
        self.mot_de_passe = mot_de_passe
        self.var_test.set(self._texte("courriel.test.ok"))

    def page_stack(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        # grille plutôt que pack : avec une seule rangée extensible, le tableau prend la
        # place restante et le formulaire garde la sienne. En pack(), le formulaire avait
        # été écrasé à zéro pixel — visible seulement sur une capture.
        page.columnconfigure(0, weight=1)
        page.rowconfigure(2, weight=1)

        ttk.Label(page, text=self._texte("stack.titre"),
                  font=self._titre(14)).grid(row=0, column=0, sticky="w")
        ttk.Label(page, text=self._texte("stack.explication"), wraplength=690,
                  justify="left").grid(row=1, column=0, sticky="w", pady=(6, 10))

        cadre = ttk.Frame(page)
        cadre.grid(row=2, column=0, sticky="nsew")
        self.arbre = ttk.Treeview(cadre, columns=("mots",), show="tree headings", height=6)
        self.arbre.heading("#0", text=self._texte("stack.nom"))
        self.arbre.heading("mots", text=self._texte("stack.mots"))
        self.arbre.column("#0", width=180)
        self.arbre.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(cadre, orient="vertical", command=self.arbre.yview).pack(side="right",
                                                                              fill="y")
        self.arbre.bind("<<TreeviewSelect>>", self._stack_selection)
        self._charger_stack()

        form = ttk.LabelFrame(page, text=self._texte("stack.ajouter"), padding=8)
        form.grid(row=3, column=0, sticky="ew", pady=(10, 0))
        form.columnconfigure(1, weight=1)

        self.var_stack_nom = tk.StringVar()
        self.var_stack_mots = tk.StringVar()

        ttk.Label(form, text=self._texte("stack.nom")).grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.var_stack_nom, width=24).grid(
            row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(form, text=self._texte("stack.mots")).grid(row=1, column=0, sticky="w",
                                                             pady=(6, 0))
        ttk.Entry(form, textvariable=self.var_stack_mots).grid(
            row=1, column=1, sticky="ew", padx=(8, 0), pady=(6, 0))

        actions = ttk.Frame(form)
        actions.grid(row=2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Button(actions, text=self._texte("stack.enregistrer"),
                   command=self._stack_enregistrer).pack(side="left")
        ttk.Button(actions, text=self._texte("stack.supprimer"),
                   command=self._stack_supprimer).pack(side="left", padx=8)
        ttk.Button(actions, text=self._texte("stack.reinitialiser"),
                   command=self._stack_reinitialiser).pack(side="left")
        ttk.Label(form, text=self._texte("stack.aide"), foreground="#555").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(6, 0))

        barre = ttk.Frame(page)
        barre.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        ttk.Button(barre, text=self._texte("wizard.precedent"),
                   command=self.page_courriel).pack(side="left")
        ttk.Button(barre, text=self._texte("wizard.suivant"),
                   command=self.page_planification).pack(side="right")

    def _charger_stack(self) -> None:
        """Charge la stack à éditer : celle enregistrée, sinon celle du moteur."""
        stack = self.perimetre.get("stack") or {}
        if not stack:
            try:
                stack = engine.stack_par_defaut(self.dossier)
            except Exception as exc:    # noqa: BLE001 - on l'affiche, on ne l'avale plus
                # Une liste vide sans explication est un bug qu'on a déjà livré une fois :
                # le moteur ne s'importait pas dans l'exe. Maintenant ça se voit.
                message = f"Stack par defaut indisponible : {type(exc).__name__}: {exc}"
                self.stack = {}
                self.arbre.insert("", "end", text="!", values=(message,))
                logging_setup.journaliser(paths.chemin_journal()).error(message)
                return
        self.stack = {nom: list(mots) for nom, mots in stack.items()}
        self._rafraichir_stack()

    def _rafraichir_stack(self) -> None:
        for item in self.arbre.get_children():
            self.arbre.delete(item)
        for nom, mots in self.stack.items():
            self.arbre.insert("", "end", text=nom, values=(", ".join(mots),))
        self.perimetre["stack"] = {nom: list(mots) for nom, mots in self.stack.items()}

    def _stack_selection(self, _event=None) -> None:
        selection = self.arbre.selection()
        if not selection:
            return
        self.var_stack_nom.set(self.arbre.item(selection[0], "text"))
        self.var_stack_mots.set(self.arbre.item(selection[0], "values")[0])

    def _stack_enregistrer(self) -> None:
        nom = self.var_stack_nom.get().strip()
        mots = [mot.strip() for mot in self.var_stack_mots.get().split(",") if mot.strip()]
        if not nom or not mots:
            messagebox.showerror(self._texte("commun.erreur"), self._texte("stack.aide"))
            return
        # Renommer une entrée sélectionnée ne doit pas laisser l'ancienne derrière elle.
        selection = self.arbre.selection()
        if selection:
            ancien = self.arbre.item(selection[0], "text")
            if ancien != nom:
                self.stack.pop(ancien, None)
        self.stack[nom] = mots
        self._rafraichir_stack()

    def _stack_supprimer(self) -> None:
        selection = self.arbre.selection()
        if not selection:
            return
        self.stack.pop(self.arbre.item(selection[0], "text"), None)
        self.var_stack_nom.set("")
        self.var_stack_mots.set("")
        self._rafraichir_stack()

    def _stack_reinitialiser(self) -> None:
        try:
            reference = engine.stack_par_defaut(self.dossier)
        except Exception:               # noqa: BLE001 - moteur absent : on ne casse rien
            reference = {}
        self.stack = {nom: list(mots) for nom, mots in reference.items()}
        self._rafraichir_stack()

    def page_planification(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        ttk.Label(page, text=self._texte("planif.titre"),
                  font=self._titre(14)).pack(anchor="w")

        cadre = ttk.Frame(page)
        cadre.pack(fill="x", pady=(12, 0))
        cadre.columnconfigure(1, weight=1)

        self.var_heure = tk.StringVar(value=self.brouillon.get("heure", "06:00"))
        self.var_fenetre = tk.StringVar(value=str(self.brouillon.get("window_hours", 27)))
        self.var_fuseau = tk.StringVar(value=self.brouillon.get("timezone",
                                                                configuration.FUSEAU_PAR_DEFAUT))

        ttk.Label(cadre, text=self._texte("planif.heure")).grid(row=0, column=0, sticky="w",
                                                                pady=4)
        ttk.Entry(cadre, textvariable=self.var_heure, width=10).grid(row=0, column=1,
                                                                     sticky="w")
        ttk.Label(cadre, text=self._texte("planif.fenetre")).grid(row=1, column=0, sticky="w",
                                                                  pady=4)
        ttk.Entry(cadre, textvariable=self.var_fenetre, width=10).grid(row=1, column=1,
                                                                       sticky="w")
        ttk.Label(cadre, text=self._texte("planif.fuseau")).grid(row=2, column=0, sticky="w",
                                                                 pady=4)
        valeurs = sorted(set(FUSEAUX_COURANTS) | {self.var_fuseau.get() or ""})
        self.fuseaux_proposes = [valeur for valeur in valeurs if valeur]
        self.combo_fuseau = ttk.Combobox(cadre, textvariable=self.var_fuseau,
                                         values=self.fuseaux_proposes, width=30)
        self.combo_fuseau.grid(row=2, column=1, sticky="w")
        ttk.Label(cadre, text=self._texte("planif.fuseau.aide"), foreground="#555").grid(
            row=3, column=0, columnspan=2, sticky="w")

        barre = ttk.Frame(page)
        barre.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(barre, text=self._texte("wizard.precedent"),
                   command=self.page_stack).pack(side="left")
        ttk.Button(barre, text=self._texte("wizard.terminer"),
                   command=self._terminer).pack(side="right")

    def _terminer(self) -> None:
        self.brouillon["heure"] = self.var_heure.get().strip()
        self.brouillon["window_hours"] = self.var_fenetre.get().strip()
        self.brouillon["timezone"] = self.var_fuseau.get().strip()

        problemes = configuration.valider(self.brouillon)
        if problemes:
            messagebox.showerror(self._texte("commun.erreur"), ", ".join(problemes))
            return
        if not self.mot_de_passe:
            messagebox.showerror(self._texte("commun.erreur"),
                                 self._texte("courriel.test.echec"))
            return

        configuration.enregistrer(self.dossier, self.brouillon)
        secrets.enregistrer_jetons(paths.chemin_secret(),
                                   {"smtp_password": self.mot_de_passe})
        # Le diagnostic lit l'état en mémoire : sans cette mise à jour, il continue
        # d'annoncer « aucun mot de passe » alors qu'il vient d'être écrit. Un diagnostic
        # doit dire ce qui est, pas ce qui était au démarrage.
        self.jetons = {"smtp_password": self.mot_de_passe}
        configuration.enregistrer_perimetre(self.dossier, self.perimetre)
        self._programmer()
        self.reglages = dict(self.brouillon)
        self.afficher_panneau()

    def _programmer(self) -> None:
        """Enregistre la tâche quotidienne ; un échec ne doit pas empêcher d'utiliser l'app."""
        try:
            commande = [runner.commande_moteur("run")[0]]
            arguments = " ".join(runner.commande_moteur("run")[1:])
            xml = schedule.construire_xml(Path(commande[0]), heure=self.brouillon["heure"],
                                          arguments=arguments)
            schedule.installer(xml)
        except Exception:                       # noqa: BLE001 - pas de tâche, pas de drame
            pass

    # --- panneau -----------------------------------------------------------
    def afficher_panneau(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        ttk.Label(page, text=self._texte("app.titre"),
                  font=self._titre(16)).pack(anchor="w")

        # Bandeau de mise à jour : rempli seulement si une version plus récente existe.
        self.var_maj = tk.StringVar(value="")
        self.lbl_maj = ttk.Label(page, textvariable=self.var_maj, foreground="#8a6d3b")
        self.lbl_maj.pack(anchor="w")
        self.var_statut = tk.StringVar(value=self._texte("panneau.jamais"))
        ttk.Label(page, textvariable=self.var_statut).pack(anchor="w", pady=(4, 2))

        self.var_prochaine = tk.StringVar(value="")
        ttk.Label(page, textvariable=self.var_prochaine).pack(anchor="w", pady=(0, 12))
        self._afficher_prochaine()

        boutons = ttk.Frame(page)
        boutons.pack(anchor="w", pady=4)
        ttk.Button(boutons, text=self._texte("panneau.lancer"),
                   command=lambda: self._lancer("run")).grid(row=0, column=0, padx=(0, 8),
                                                             pady=4)
        ttk.Button(boutons, text=self._texte("panneau.apercu"),
                   command=lambda: self._lancer("preview")).grid(row=0, column=1, padx=8)
        ttk.Button(boutons, text=self._texte("panneau.rapport"),
                   command=self._ouvrir_rapport).grid(row=0, column=2, padx=8)
        ttk.Button(boutons, text=self._texte("panneau.sources"),
                   command=lambda: self._lancer("sources", preflight=False)).grid(
            row=1, column=0, padx=(0, 8), pady=4)
        ttk.Button(boutons, text=self._texte("panneau.liens"),
                   command=lambda: self._lancer("liens", preflight=False)).grid(
            row=1, column=1, padx=8)
        ttk.Button(boutons, text=self._texte("panneau.journal"),
                   command=self._ouvrir_journal).grid(row=1, column=2, padx=8)
        ttk.Button(boutons, text=self._texte("panneau.diagnostic"),
                   command=self._ouvrir_diagnostic).grid(row=2, column=0, padx=(0, 8), pady=4)

        bas = ttk.Frame(page)
        bas.pack(side="bottom", fill="x")
        ttk.Button(bas, text=self._texte("panneau.effacer"),
                   command=self._effacer_donnees).pack(side="right")
        ttk.Button(bas, text=self._texte("about.titre"),
                   command=self._ouvrir_about).pack(side="left")
        # Retour dans l'assistant : sans cette porte, changer de mot de passe ou d'adresse
        # était impossible une fois la configuration enregistrée — le panneau n'offrait
        # rien, et l'assistant ne s'affiche plus quand une adresse existe déjà.
        ttk.Button(bas, text=self._texte("panneau.reglages"),
                   command=self.page_courriel).pack(side="left", padx=(8, 0))

        # Taille de texte : agrandir tout, pas seulement les titres — c'est un réglage
        # d'accessibilité, pas une coquetterie.
        ttk.Label(bas, text=self._texte("panneau.taille")).pack(side="left", padx=(16, 4))
        choix_taille = ttk.Combobox(bas, values=["9", "10", "12", "14"], width=4,
                                    state="readonly")
        choix_taille.set(str(self.taille))
        choix_taille.pack(side="left")
        choix_taille.bind("<<ComboboxSelected>>",
                          lambda _e: self._changer_taille(int(choix_taille.get())))

        self._verifier_mise_a_jour()

    def _afficher_prochaine(self) -> None:
        try:
            prochaine = schedule.prochaine_execution()
        except Exception:                       # noqa: BLE001 - pas de tâche : rien à dire
            prochaine = None
        if prochaine:
            self.var_prochaine.set(f"{self._texte('panneau.prochaine')} : {prochaine[:19]}")

    def _afficher_statut(self, texte: str) -> None:
        self.var_statut.set(texte)

    def _changer_taille(self, taille: int) -> None:
        self.reglages["taille_texte"] = taille
        configuration.enregistrer(self.dossier, self.reglages)
        self._appliquer_taille(taille)
        self.afficher_panneau()

    def _verifier_mise_a_jour(self) -> None:
        """Une seule vérification par session : la fenêtre est reconstruite à chaque page."""
        if self._maj_verifiee:
            return
        self._maj_verifiee = True

        def travail() -> None:
            from . import updates

            derniere = updates.derniere_publiee()
            if derniere and updates.plus_recente(version_actuelle, derniere):
                self.racine.after(0, lambda: self.var_maj.set(
                    self._texte("panneau.maj").format(version=derniere)))

        threading.Thread(target=travail, daemon=True).start()

    def _lancer(self, mode: str, preflight: bool = True) -> None:
        if not self.mot_de_passe:
            self._afficher_statut(self._texte("courriel.test.echec"))
            return
        self._afficher_statut("…")

        def travail() -> None:
            journal = logging_setup.journaliser(paths.chemin_journal())
            resultat = runner.executer(self.reglages, self.mot_de_passe, journal,
                                       mode=mode, dossier=self.dossier, preflight=preflight)
            libelles = {"ok": "OK", "erreur": "erreur", "reseau": "reseau indisponible",
                        "deja_en_cours": "deja en cours"}
            self.racine.after(0, lambda: self._afficher_statut(
                f"{self._texte('panneau.statut')} : {libelles.get(resultat.statut, resultat.statut)}"
                f" ({resultat.duree:.0f} s)"))

        threading.Thread(target=travail, daemon=True).start()

    def _ouvrir_rapport(self) -> None:
        for nom in ("preview.html", "rapport.html"):
            chemin = self.dossier / nom
            if chemin.exists():
                webbrowser.open(chemin.as_uri())
                return
        messagebox.showinfo(self._texte("panneau.rapport"),
                            self._texte("panneau.jamais"))

    def _ouvrir_journal(self) -> None:
        fenetre = tk.Toplevel(self.racine)
        fenetre.title(self._texte("panneau.journal"))
        fenetre.geometry("820x480")
        texte = tk.Text(fenetre, wrap="none", font=("Consolas", 9))
        texte.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(fenetre, orient="vertical", command=texte.yview).pack(side="right",
                                                                           fill="y")
        chemin = paths.chemin_journal()
        if chemin.exists():
            lignes = chemin.read_text(encoding="utf-8", errors="replace").splitlines()
            texte.insert("end", "\n".join(lignes[-800:]))

    def _ouvrir_diagnostic(self) -> None:
        """Le diagnostic interroge le réseau et le serveur SMTP : il tourne hors du fil UI."""
        self._afficher_statut("…")

        def travail() -> None:
            from . import doctor

            texte = doctor.rapport(doctor.collecter(
                dossier=self.dossier, reglages=self.reglages,
                # Relu depuis le disque, et non depuis la mémoire : c'est le seul moyen
                # d'être sûr que ce que le diagnostic affirme est bien enregistré.
                jetons=secrets.charger_jetons(paths.chemin_secret()),
                tester_smtp=mail.verifier_connexion))
            self.racine.after(0, lambda: self._montrer_rapport(texte))

        threading.Thread(target=travail, daemon=True).start()

    def _montrer_rapport(self, texte: str) -> None:
        lignes = [ligne for ligne in texte.splitlines() if ligne.strip()]
        self._afficher_statut(lignes[-1] if lignes else "")

        fenetre = tk.Toplevel(self.racine)
        fenetre.title(self._texte("panneau.diagnostic"))
        fenetre.geometry("760x420")
        cadre = ttk.Frame(fenetre, padding=8)
        cadre.pack(fill="both", expand=True)
        zone = tk.Text(cadre, wrap="none", font=("Consolas", 9))
        zone.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(cadre, orient="vertical", command=zone.yview).pack(side="right",
                                                                        fill="y")
        zone.insert("end", texte)
        zone.configure(state="disabled")
        barre = ttk.Frame(fenetre, padding=(8, 0, 8, 8))
        barre.pack(fill="x")
        ttk.Button(barre, text=self._texte("commun.copier"),
                   command=lambda: self._copier(texte)).pack(side="right")

    def _copier(self, texte: str) -> None:
        self.racine.clipboard_clear()
        self.racine.clipboard_append(texte)

    def _ouvrir_about(self) -> None:
        fenetre = tk.Toplevel(self.racine)
        fenetre.title(self._texte("about.titre"))
        fenetre.resizable(False, False)
        verrou = {}
        try:
            import json

            verrou = json.loads((paths.dossier_executable() / "vendor" / "engine.json")
                                .read_text(encoding="utf-8"))
        except Exception:                       # noqa: BLE001 - pas de verrou : pas bloquant
            verrou = {}
        lignes = [f"SecDailyBrief 1.0.0",
                  f"{self._texte('about.moteur')}: {verrou.get('commit', '?')}",
                  f"{self._texte('about.licence')}: MIT",
                  f"{self._texte('about.depot')}: {URL_DEPOT}",
                  "",
                  self._texte("app.pied")]
        ttk.Label(fenetre, text="\n".join(lignes), padding=16, justify="left").pack()
        ttk.Button(fenetre, text=self._texte("commun.annuler"),
                   command=fenetre.destroy).pack(pady=(0, 12))

    def _effacer_donnees(self) -> None:
        if not messagebox.askyesno(self._texte("panneau.effacer"),
                                   self._texte("panneau.effacer.confirme")):
            return
        for chemin in (paths.chemin_config(), paths.chemin_secret(),
                       configuration.chemin_perimetre(self.dossier), paths.chemin_journal()):
            try:
                Path(chemin).unlink(missing_ok=True)
            except OSError:
                pass
        try:
            schedule.supprimer()
        except Exception:                       # noqa: BLE001 - pas de tâche : rien à retirer
            pass
        self.racine.destroy()


def lancer() -> int:
    dossier = paths.s_assurer_dossier()
    racine = tk.Tk()
    Application(racine, dossier)
    racine.mainloop()
    return 0
