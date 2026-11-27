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
import webbrowser
import tkinter as tk
import tkinter.font as tkfont
from pathlib import Path
from tkinter import messagebox, ttk

from . import config as configuration
from . import __version__ as version_actuelle
from . import engine, fuseau, historique, i18n, logging_setup, mail, paths, runner, schedule, secrets, updates

TAILLE_MIN = (760, 540)
URL_MOT_DE_PASSE = "https://myaccount.google.com/apppasswords"
URL_SOUTIEN = "https://www.buymeacoffee.com/bsky.scl"
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


def reglages_initiaux(dossier: Path) -> dict:
    """Réglages de départ : ceux du fichier, ou les défauts avec l'heure de cette machine.

    La détection ne s'applique qu'à une première exécution : une fois l'utilisateur passé par
    l'assistant, son choix de fuseau lui appartient et n'est jamais écrasé.
    """
    reglages = configuration.charger(dossier)
    if not configuration.chemin_config(dossier).exists():
        reglages["timezone"] = fuseau.zone_iana()
    return reglages


class Application:
    """Une fenêtre, deux visages : l'assistant au premier lancement, le panneau ensuite."""

    def __init__(self, racine: tk.Tk, dossier: Path) -> None:
        self.racine = racine
        self.dossier = dossier
        self.reglages = reglages_initiaux(dossier)
        self.jetons = secrets.charger_jetons(paths.chemin_secret())
        self.perimetre = configuration.charger_perimetre(dossier)

        self.langue = self.reglages.get("langue") or i18n.apparier_langue_systeme(
            langue_du_systeme())
        self.textes = i18n.textes(self.langue)
        self.mot_de_passe = self.jetons.get("smtp_password", "")
        self.brouillon = dict(self.reglages)
        self.taille = int(self.reglages.get("taille_texte") or 10)
        self._maj_verifiee = False
        self._perimetre_en_attente = configuration.valider_perimetre(self.perimetre)
        # Les réglages ne sont contrôlés au démarrage que s'il y en a : sur une première
        # exécution, c'est l'assistant qui les recueille, pas une boîte d'erreur.
        self._reglages_en_attente = (configuration.valider(self.reglages)
                                     if self.reglages.get("email_user") else [])

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
        if page == "panneau":
            self.afficher_panneau()
        elif page and hasattr(self, f"page_{page}"):
            getattr(self, f"page_{page}")()

        # Après l'affichage : un fichier fautif doit se dire une fois la fenêtre visible,
        # sinon la boîte de dialogue apparaît sur un écran vide.
        if self._perimetre_en_attente or self._reglages_en_attente:
            self.racine.after(200, self._signaler_etat)

    def _signaler_etat(self) -> None:
        if self._perimetre_en_attente:
            self._signaler_perimetre()
        if self._reglages_en_attente:
            self._signaler_reglages()

    def _signaler_reglages(self) -> None:
        """Nomme les réglages fautifs et propose de les corriger.

        Les remettre à zéro serait plus simple, mais effacerait l'adresse de l'utilisateur :
        on ouvre la page qui permet de les corriger, et c'est lui qui décide.
        """
        problemes = self._reglages_en_attente
        self._reglages_en_attente = []
        logging_setup.journaliser(paths.chemin_journal()).error(
            "Reglages invalides : %s", "; ".join(problemes))
        details = "\n".join(f"• {probleme}" for probleme in problemes)
        question = self._texte("reglages.invalide").format(details=details)
        if messagebox.askyesno(self._texte("commun.information"), question):
            self.page_courriel()

    def _signaler_perimetre(self) -> None:
        """Nomme la faute du fichier de périmètre, et propose de repartir de l'exemple.

        Le moteur, lui, ne la découvre qu'au run — quatre minutes après le clic, dans le
        journal. À l'ouverture, elle est encore réparable.
        """
        problemes = self._perimetre_en_attente
        self._perimetre_en_attente = []
        message = "; ".join(problemes)
        logging_setup.journaliser(paths.chemin_journal()).error(
            "Perimetre invalide : %s", message)
        details = "\n".join(f"• {probleme}" for probleme in problemes)
        question = self._texte("perimetre.invalide").format(details=details)
        if messagebox.askyesno(self._texte("commun.information"), question):
            self._restaurer_perimetre()

    def _restaurer_perimetre(self) -> None:
        """Met le fichier fautif de côté et repart des valeurs d'exemple du moteur."""
        chemin = configuration.chemin_perimetre(self.dossier)
        if chemin.exists():
            try:
                chemin.replace(chemin.with_name(chemin.name + ".invalide"))
            except OSError:                 # fichier verrouillé : on l'écrasera de toute façon
                pass
        self.perimetre = {}
        configuration.enregistrer_perimetre(self.dossier, {})
        self.brouillon["perimetre_restaure"] = True

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
    def _entete(self, parent, hauteur: int = 62) -> ttk.Frame:
        """Bandeau d'identité, commun au panneau et aux pages de l'assistant.

        Encapsulé dans son propre cadre : la page de la stack gère ses enfants en grid,
        et mêler pack et grid dans un même conteneur fait échouer Tk.
        """
        cadre = ttk.Frame(parent)
        self._bandeau(cadre, hauteur=hauteur)
        return cadre

    def page_langue(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        self._entete(page).pack(fill="x")
        ttk.Label(page, text=self._texte("wizard.bienvenue"),
                  font=self._titre(13)).pack(anchor="w", padx=14, pady=(10, 0))
        ttk.Label(page, text=self._texte("wizard.intro"), wraplength=680,
                  justify="left").pack(anchor="w", padx=14, pady=(8, 16))
        ttk.Label(page, text=self._texte("wizard.langue")).pack(anchor="w", padx=14)

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

        self._entete(page).pack(fill="x")
        ttk.Label(page, text=self._texte("consent.titre"),
                  font=self._titre(13)).pack(anchor="w", padx=14, pady=(10, 0))
        ttk.Label(page, text=self._texte("consent.texte"), wraplength=690,
                  justify="left").pack(anchor="w", padx=14, pady=(8, 8))
        ttk.Label(page, text=self._texte("consent.pause"), wraplength=690,
                  justify="left").pack(anchor="w", padx=14, pady=(0, 12))

        domaines = domaines_contactes()
        cadre = ttk.LabelFrame(page, text=f"{self._texte('consent.domaines')} "
                                          f"({len(domaines)})", padding=8)
        cadre.pack(fill="both", expand=True, padx=14)
        liste = tk.Listbox(cadre, height=8, activestyle="none")
        for domaine in domaines:
            liste.insert("end", domaine)
        liste.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(cadre, orient="vertical", command=liste.yview).pack(side="right",
                                                                         fill="y")

        # La case reprend l'état enregistré : revenir sur cette page pour changer la langue
        # ne doit pas redemander un consentement déjà donné — sinon « Suivant » reste
        # désactivé et l'utilisateur croit être bloqué.
        self.consentement = tk.BooleanVar(value=bool(self.brouillon.get("consentement")))
        ttk.Checkbutton(page, text=self._texte("consent.accepte"),
                        variable=self.consentement,
                        command=self._maj_bouton_consentement).pack(anchor="w", pady=(8, 0))

        barre = ttk.Frame(page)
        barre.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(barre, text=self._texte("wizard.precedent"),
                   command=self.page_langue).pack(side="left")
        # Désactivé tant que la case n'est pas cochée : une case qui ne conditionne rien
        # ne demande rien, et laisserait croire à un consentement qui n'a pas eu lieu.
        self.bouton_consentement = ttk.Button(
            barre, text=self._texte("wizard.suivant"), command=self.page_courriel,
            state="normal" if self.consentement.get() else "disabled")
        self.bouton_consentement.pack(side="right")

    def _maj_bouton_consentement(self) -> None:
        self.bouton_consentement.configure(
            state="normal" if self.consentement.get() else "disabled")

    def page_courriel(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        self._entete(page).pack(fill="x")
        ttk.Label(page, text=self._texte("courriel.titre"),
                  font=self._titre(13)).pack(anchor="w", padx=14, pady=(10, 0))

        cadre = ttk.Frame(page)
        cadre.pack(fill="x", padx=14, pady=(12, 0))
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

        # L'aide et le lien sur deux lignes : côte à côte, ils se disputaient la largeur et
        # la fenêtre s'élargissait à 803 px pour les faire tenir, texte tronqué.
        aide = ttk.Frame(page)
        aide.pack(fill="x", padx=14, pady=(10, 0))
        ttk.Label(aide, text=self._texte("courriel.aide"), wraplength=700,
                  justify="left").pack(anchor="w")
        ttk.Button(aide, text=self._texte("courriel.lien"),
                   command=lambda: webbrowser.open(URL_MOT_DE_PASSE)).pack(anchor="w",
                                                                           pady=(6, 0))

        self.var_test = tk.StringVar(value="")
        ttk.Label(page, textvariable=self.var_test, foreground="#1b5e20").pack(anchor="w",
                                                                               pady=(8, 0))

        barre = ttk.Frame(page)
        barre.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(barre, text=self._texte("wizard.precedent"),
                   command=self._precedent_courriel).pack(side="left")
        ttk.Button(barre, text=self._texte("courriel.tester"),
                   command=self._tester_envoi).pack(side="left", padx=8)
        ttk.Button(barre, text=self._texte("wizard.suivant"),
                   command=self._courriel_suivant).pack(side="right")

    def _precedent_courriel(self) -> None:
        """« Précédent » ramène au panneau quand on vient de « Réglages ».

        Ouvert par le panneau, l'assistant démarrait sur la page courriel et « Précédent »
        remontait vers le consentement puis la langue : impossible de revenir au panneau, et
        les canaux d'alerte, situés en fin de parcours, devenaient inatteignables.
        """
        if self.reglages.get("email_user"):
            self.afficher_panneau()
        else:
            self.page_consentement()

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
        page.rowconfigure(3, weight=1)

        self._entete(page).grid(row=0, column=0, sticky="ew")
        ttk.Label(page, text=self._texte("stack.titre"),
                  font=self._titre(13)).grid(row=1, column=0, sticky="w", padx=14,
                                             pady=(10, 0))
        ttk.Label(page, text=self._texte("stack.explication"), wraplength=690,
                  justify="left").grid(row=2, column=0, sticky="w", padx=14, pady=(6, 10))

        cadre = ttk.Frame(page)
        cadre.grid(row=3, column=0, sticky="nsew", padx=14)
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
        form.grid(row=4, column=0, sticky="ew", padx=14, pady=(10, 0))
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
        barre.grid(row=5, column=0, sticky="ew", padx=14, pady=(10, 0))
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

        self._entete(page).pack(fill="x")
        ttk.Label(page, text=self._texte("planif.titre"),
                  font=self._titre(13)).pack(anchor="w", padx=14, pady=(10, 0))

        cadre = ttk.Frame(page)
        cadre.pack(fill="x", padx=14, pady=(12, 0))
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

        self.var_alertes = tk.BooleanVar(
            value=bool(self.brouillon.get("alertes_immediates", True)))
        ttk.Checkbutton(cadre, text=self._texte("planif.alertes"),
                        variable=self.var_alertes).grid(row=4, column=0, columnspan=2,
                                                        sticky="w", pady=(10, 0))
        ttk.Label(cadre, text=self._texte("planif.alertes.aide"), foreground="#555").grid(
            row=5, column=0, columnspan=2, sticky="w")

        # Canaux de l'alerte. Un webhook est un secret : il est rangé avec le mot de passe
        # SMTP, chiffré par DPAPI, et non dans config.json.
        canaux = ttk.Frame(page)
        canaux.pack(fill="x", padx=14, pady=(10, 0))
        canaux.columnconfigure(1, weight=1)

        self.var_mail = tk.BooleanVar(value=bool(self.brouillon.get("alerte_mail", True)))
        self.var_slack = tk.StringVar(value=self.jetons.get("slack_webhook", ""))
        self.var_discord = tk.StringVar(value=self.jetons.get("discord_webhook", ""))
        self.var_telegram_token = tk.StringVar(value=self.jetons.get("telegram_token", ""))
        self.var_telegram_chat = tk.StringVar(value=self.jetons.get("telegram_chat", ""))
        self.var_slack_on = tk.BooleanVar(value=bool(self.brouillon.get("alerte_slack", False)))
        self.var_discord_on = tk.BooleanVar(
            value=bool(self.brouillon.get("alerte_discord", False)))
        self.var_telegram_on = tk.BooleanVar(
            value=bool(self.brouillon.get("alerte_telegram", False)))

        ttk.Label(canaux, text=self._texte("alertes.canaux"),
                  font=self._titre(11)).grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(canaux, text=self._texte("alertes.mail"),
                        variable=self.var_mail).grid(row=1, column=0, columnspan=2, sticky="w")
        ttk.Checkbutton(canaux, text=self._texte("alertes.slack"),
                        variable=self.var_slack_on).grid(row=2, column=0, sticky="w", pady=(6, 0))
        ttk.Entry(canaux, textvariable=self.var_slack, width=52).grid(
            row=2, column=1, sticky="we", pady=(6, 0))
        ttk.Checkbutton(canaux, text=self._texte("alertes.discord"),
                        variable=self.var_discord_on).grid(row=3, column=0, sticky="w")
        ttk.Entry(canaux, textvariable=self.var_discord, width=52).grid(
            row=3, column=1, sticky="we")
        ttk.Checkbutton(canaux, text=self._texte("alertes.telegram"),
                        variable=self.var_telegram_on).grid(row=4, column=0, sticky="w")
        telegram = ttk.Frame(canaux)
        telegram.grid(row=4, column=1, sticky="we")
        telegram.columnconfigure(0, weight=1)
        ttk.Entry(telegram, textvariable=self.var_telegram_token, width=34).grid(
            row=0, column=0, sticky="we")
        ttk.Entry(telegram, textvariable=self.var_telegram_chat, width=16).grid(
            row=0, column=1, sticky="w", padx=(6, 0))
        ttk.Label(canaux, text=self._texte("alertes.aide"), foreground="#555").grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(6, 0))

        barre = ttk.Frame(page)
        barre.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(barre, text=self._texte("wizard.precedent"),
                   command=self._precedent_planification).pack(side="left")
        ttk.Button(barre, text=self._texte("wizard.terminer"),
                   command=self._terminer).pack(side="right")

    def _collecter_canaux(self) -> None:
        """Mémorise les canaux saisis, sans rien écrire sur disque.

        Sans cela, revenir en arrière puis avancer à nouveau vidait les adresses de webhook :
        la page les relisait depuis le fichier de secrets, qui n'avait pas encore été écrit.
        """
        self.brouillon["alerte_mail"] = bool(self.var_mail.get())
        self.brouillon["alerte_slack"] = bool(self.var_slack_on.get())
        self.brouillon["alerte_discord"] = bool(self.var_discord_on.get())
        self.brouillon["alerte_telegram"] = bool(self.var_telegram_on.get())
        self.jetons["slack_webhook"] = self.var_slack.get().strip()
        self.jetons["discord_webhook"] = self.var_discord.get().strip()
        self.jetons["telegram_token"] = self.var_telegram_token.get().strip()
        self.jetons["telegram_chat"] = self.var_telegram_chat.get().strip()

    def _precedent_planification(self) -> None:
        self._collecter_canaux()
        self.page_stack()

    def _terminer(self) -> None:
        self.brouillon["heure"] = self.var_heure.get().strip()
        self.brouillon["alertes_immediates"] = bool(self.var_alertes.get())
        self._collecter_canaux()
        self.brouillon["window_hours"] = self.var_fenetre.get().strip()
        self.brouillon["timezone"] = self.var_fuseau.get().strip()
        # Arriver au bout de l'assistant vaut consentement : il a été demandé en chemin.
        self.brouillon["consentement"] = True

        problemes = configuration.valider(self.brouillon)
        if problemes:
            messagebox.showerror(self._texte("commun.erreur"), ", ".join(problemes))
            return
        if not self.mot_de_passe:
            messagebox.showerror(self._texte("commun.erreur"),
                                 self._texte("courriel.test.echec"))
            return

        configuration.enregistrer(self.dossier, self.brouillon)
        # Un webhook *est* un secret : l'URL suffit à publier. Il part donc dans le même
        # fichier chiffré que le mot de passe SMTP, jamais dans config.json.
        jetons = dict(self.jetons)
        jetons.update({
            "smtp_password": self.mot_de_passe,
            "slack_webhook": self.var_slack.get().strip(),
            "discord_webhook": self.var_discord.get().strip(),
            "telegram_token": self.var_telegram_token.get().strip(),
            "telegram_chat": self.var_telegram_chat.get().strip(),
        })
        secrets.enregistrer_jetons(paths.chemin_secret(), jetons)
        # Le diagnostic lit l'état en mémoire : sans cette mise à jour, il continue
        # d'annoncer « aucun mot de passe » alors qu'il vient d'être écrit. Un diagnostic
        # doit dire ce qui est, pas ce qui était au démarrage.
        self.jetons = jetons
        configuration.enregistrer_perimetre(self.dossier, self.perimetre)
        self._programmer()
        self.reglages = dict(self.brouillon)
        self.afficher_panneau()

    def _programmer(self) -> None:
        """Enregistre les tâches ; un échec ne doit pas empêcher d'utiliser l'application."""
        try:
            # L'application, pas le moteur : `--run` passe par le pré-vol, le verrou, le
            # journal et le dossier de données. `--moteur` sauterait tout cela.
            commande = runner.commande_application("run")
            xml = schedule.construire_xml(Path(commande[0]), heure=self.brouillon["heure"],
                                          arguments=" ".join(commande[1:]))
            schedule.installer(xml)
        except Exception:                       # noqa: BLE001 - pas de tâche, pas de drame
            pass
        # La tâche d'alerte suit la case à cocher : installée quand elle est cochée, retirée
        # sinon. C'est ce qui la distingue du rapport quotidien, qui reste la tâche principale.
        try:
            if self.brouillon.get("alertes_immediates"):
                commande = runner.commande_application("alerte")
                xml = schedule.construire_xml_alerte(Path(commande[0]),
                                                    arguments=" ".join(commande[1:]))
                schedule.installer(xml, nom=schedule.NOM_TACHE_ALERTE)
            elif schedule.existe(schedule.NOM_TACHE_ALERTE):
                schedule.supprimer(schedule.NOM_TACHE_ALERTE)
        except Exception:                       # noqa: BLE001
            pass

    # --- panneau -----------------------------------------------------------
    def _bandeau(self, parent, hauteur: int = 72) -> tk.Canvas:
        """Bandeau dégradé, dessiné à la volée.

        Aucune image livrée en dur : un dégradé dessiné suit la largeur de la fenêtre et
        reste net à toutes les échelles, là où un PNG se floute en 125 %.
        """
        canevas = tk.Canvas(parent, height=hauteur, highlightthickness=0, bd=0,
                            bg=self._fond())
        canevas.pack(fill="x")
        self._charger_logo()

        def dessiner(_event=None) -> None:
            largeur = max(canevas.winfo_width(), 200)
            canevas.delete("degrade")
            for i in range(hauteur):
                part = i / max(1, hauteur - 1)
                couleur = "#%02x%02x%02x" % (int(240 - 30 * part),
                                              int(242 - 28 * part),
                                              int(245 - 26 * part))
                canevas.create_rectangle(0, i, largeur, i + 1, fill=couleur, outline="",
                                         tags="degrade")
            canevas.create_rectangle(0, hauteur - 1, largeur, hauteur, fill="#b9bfc7",
                                     outline="", tags="degrade")
            canevas.delete("titre")
            # Le logo occupe la place d'un carré : le titre se décale d'autant, seulement
            # si l'image a bien pu être chargée.
            marge = 18
            if self._logo is not None:
                canevas.delete("logo")
                canevas.create_image(marge, hauteur // 2 - 1, anchor="w", image=self._logo,
                                     tags="logo")
                marge += self._logo.width() + 12
            canevas.create_text(marge, hauteur // 2 - 2, anchor="w",
                                text=self._texte("app.titre"), fill="#1b1d21",
                                font=self._titre(15), tags="titre")

        canevas.bind("<Configure>", dessiner)
        return canevas

    def _charger_logo(self, cote: int = 28) -> None:
        """Charge le logo une seule fois, réduit par sous-échantillonnage entier.

        tkinter ne sait pas redimensionner en douceur : on divise par un facteur entier
        (512 -> 28, facteur 18) plutôt que d'obtenir une image floue.
        """
        if getattr(self, "_logo", None) is not None:
            return
        self._logo = None
        try:
            image = tk.PhotoImage(file=str(paths.dossier_ressources() / "SecDailyBrief-512.png"))
            facteur = max(1, round(image.width() / cote))
            self._logo = image.subsample(facteur, facteur)
        except Exception:                   # noqa: BLE001 - pas de logo, pas de drame
            self._logo = None

    def _carte(self, parent):
        """Cadre en léger relief : un filet sombre, le fond du thème.

        C'est la profondeur de Captvty sans sortir du thème natif — un fond blanc
        jurerait avec les contrôles ttk, qui restent gris.
        """
        exterieur = tk.Frame(parent, bg="#c3c8cf", bd=0)
        lisere = tk.Frame(exterieur, bg="#ffffff", bd=0, height=1)
        lisere.pack(fill="x", padx=1, pady=(1, 0))
        interieur = tk.Frame(exterieur, bg=self._fond(), bd=0)
        interieur.pack(fill="both", expand=True, padx=1, pady=(0, 1))
        return exterieur, interieur

    def _fond(self) -> str:
        try:
            return str(self.racine.cget("background"))
        except Exception:                       # noqa: BLE001 - valeur de repli
            return "#f0f0f0"

    def afficher_panneau(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        self._bandeau(page, hauteur=74)

        # Bandeau de mise à jour : rempli seulement si une version plus récente existe.
        self.var_maj = tk.StringVar(value="")
        self.lbl_maj = ttk.Label(page, textvariable=self.var_maj, foreground="#8a6d3b")
        self.lbl_maj.pack(anchor="w", padx=14, pady=(8, 0))

        bas = ttk.Frame(page)
        bas.pack(side="bottom", fill="x", padx=14, pady=(0, 10))
        ttk.Button(bas, text=self._texte("panneau.effacer"),
                   command=self._effacer_donnees).pack(side="right")
        ttk.Button(bas, text=self._texte("about.titre"),
                   command=self._ouvrir_about).pack(side="left")
        # Retour dans l'assistant : sans cette porte, changer de mot de passe ou d'adresse
        # était impossible une fois la configuration enregistrée — le panneau n'offrait
        # rien, et l'assistant ne s'affiche plus quand une adresse existe déjà.
        ttk.Button(bas, text=self._texte("panneau.reglages"),
                   command=self.page_courriel).pack(side="left", padx=(8, 0))
        # Les canaux d'alerte vivaient au bout de l'assistant, sans autre porte une fois la
        # configuration enregistree : un clic depuis le panneau vaut mieux qu'un parcours.
        ttk.Button(bas, text=self._texte("panneau.alertes"),
                   command=self.page_planification).pack(side="left", padx=(8, 0))
        ttk.Button(bas, text=self._texte("panneau.don"),
                   command=self._ouvrir_don).pack(side="left", padx=(8, 0))

        cadre, contenu = self._carte(page)
        # La carte épouse son contenu : étirée sur toute la hauteur, elle laissait un
        # grand vide gris dans un cadre, ce qui ressemble à un bug d'affichage.
        cadre.pack(fill="x", padx=14, pady=10)

        self.var_statut = tk.StringVar(value=self._texte("panneau.jamais"))
        ttk.Label(contenu, textvariable=self.var_statut,
                  font=self._titre(11)).pack(anchor="w", padx=14, pady=(14, 2))

        self.var_prochaine = tk.StringVar(value="")
        ttk.Label(contenu, textvariable=self.var_prochaine).pack(anchor="w", padx=14,
                                                                 pady=(0, 10))
        self._afficher_prochaine()

        boutons = ttk.Frame(contenu)
        boutons.pack(anchor="w", padx=14)
        self.boutons_action = []

        def bouton(parent, texte, commande, ligne, colonne, marge=(8, 8)):
            widget = ttk.Button(parent, text=texte, command=commande)
            widget.grid(row=ligne, column=colonne, padx=marge, pady=4)
            self.boutons_action.append(widget)
            return widget

        bouton(boutons, self._texte("panneau.lancer"), lambda: self._lancer("run"), 0, 0)
        bouton(boutons, self._texte("panneau.apercu"), lambda: self._lancer("preview"), 0, 1)
        bouton(boutons, self._texte("panneau.rapport"), self._ouvrir_rapport, 0, 2)
        bouton(boutons, self._texte("panneau.sources"),
               lambda: self._lancer("sources", preflight=False), 1, 0)
        bouton(boutons, self._texte("panneau.liens"),
               lambda: self._lancer("liens", preflight=False), 1, 1)
        bouton(boutons, self._texte("panneau.journal"), self._ouvrir_journal, 1, 2)
        bouton(boutons, self._texte("panneau.diagnostic"), self._ouvrir_diagnostic, 2, 0)
        bouton(boutons, self._texte("panneau.historique"), self._ouvrir_historique, 2, 1)
        bouton(boutons, self._texte("panneau.verifier_maj"), self._verifier_maj, 2, 2)

        # Activité : une barre indéterminée et une phrase qui dit combien de temps ça prend.
        # Sans elles, « Lancer maintenant » ne montrait rien pendant quatre minutes.
        self.cadre_activite = ttk.Frame(contenu)
        self.barre_activite = ttk.Progressbar(self.cadre_activite, mode="indeterminate",
                                              length=220)
        self.barre_activite.pack(side="left")
        self.var_activite = tk.StringVar(value="")
        ttk.Label(self.cadre_activite, textvariable=self.var_activite).pack(side="left",
                                                                           padx=(10, 0))

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

    def _en_arriere_plan(self, travail, suite, delai: int = 250) -> None:
        """Exécute `travail` hors du fil UI, puis `suite(résultat)` dans le fil UI.

        Tk n'accepte pas d'être touché depuis un autre fil : `after()` y lève « main thread is
        not in main loop », et l'exception ne laisse qu'un avertissement pendant que la
        fenêtre reste figée dans son état d'attente. Le fil de travail dépose donc son
        résultat ; le fil principal vient le chercher.
        """
        etat = {"fait": False, "valeur": None}

        def executant() -> None:
            try:
                etat["valeur"] = travail()
            finally:
                etat["fait"] = True      # même en cas d'erreur, la fenêtre doit se débloquer

        threading.Thread(target=executant, daemon=True).start()

        def verifier() -> None:
            if not etat["fait"]:
                self.racine.after(delai, verifier)
                return
            suite(etat["valeur"])

        self.racine.after(delai, verifier)

    def _verifier_mise_a_jour(self) -> None:
        """Une seule vérification par session : la fenêtre est reconstruite à chaque page."""
        if self._maj_verifiee:
            return
        self._maj_verifiee = True

        def suite(derniere) -> None:
            if derniere and updates.plus_recente(version_actuelle, derniere):
                self.var_maj.set(self._texte("panneau.maj").format(version=derniere))

        self._en_arriere_plan(updates.derniere_publiee, suite)

    def _lancer(self, mode: str, preflight: bool = True) -> None:
        if getattr(self, "_en_cours", False):
            return                      # un second clic ne lance pas un second rapport
        # Le mot de passe ne sert qu'à envoyer. « Tester les sources » et « Vérifier les
        # liens » n'envoient rien : exiger un secret pour eux fermait deux boutons sans
        # raison, et affichait un message de courriel en échec.
        if runner.exige_mot_de_passe(mode) and not self.mot_de_passe:
            self._afficher_statut(self._texte("courriel.test.echec"))
            return

        self._en_cours = True
        self._activer_boutons(False)
        self._afficher_activite(True)

        def travail():
            journal = logging_setup.journaliser(paths.chemin_journal())
            resultat = runner.executer(self.reglages, self.mot_de_passe, journal,
                                       mode=mode, dossier=self.dossier, preflight=preflight)
            return resultat.statut, resultat.duree

        def suite(resultat) -> None:
            statut, duree = resultat
            self._en_cours = False
            self._afficher_activite(False)
            self._activer_boutons(True)
            self._afficher_statut(f"{self._texte('panneau.statut')} : "
                                  f"{self._libelle_statut(statut)} ({duree:.0f} s)")

        self._en_arriere_plan(travail, suite, delai=300)

    def _activer_boutons(self, actif: bool) -> None:
        for bouton in getattr(self, "boutons_action", []):
            bouton.configure(state="normal" if actif else "disabled")

    def _afficher_activite(self, actif: bool) -> None:
        if actif:
            self.var_activite.set(self._texte("panneau.en_cours"))
            self.cadre_activite.pack(anchor="w", pady=(6, 0))
            self.barre_activite.start(12)
        else:
            self.barre_activite.stop()
            self.cadre_activite.pack_forget()

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

    def _verifier_maj(self) -> None:
        """Interroge GitHub à la demande : le bandeau de démarrage ne suffit pas toujours."""
        if getattr(self, "_maj_en_cours", False):
            return                      # un second clic ne lance pas une seconde requête
        self._maj_en_cours = True
        statut_avant = self.var_statut.get()
        self._afficher_statut("…")

        def suite(publiee) -> None:
            self._maj_en_cours = False
            self._afficher_statut(statut_avant)
            if publiee is None:
                messagebox.showerror(self._texte("commun.erreur"), self._texte("maj.echec"))
                return
            if updates.plus_recente(version_actuelle, publiee):
                question = self._texte("maj.dispo").format(version=publiee,
                                                           actuelle=version_actuelle)
                if messagebox.askyesno(self._texte("commun.information"), question):
                    webbrowser.open(updates.PAGE)
                return
            messagebox.showinfo(self._texte("commun.information"),
                                self._texte("maj.ok").format(version=version_actuelle))

        # Hors du fil UI : l'appel a un délai de cinq secondes, et une fenêtre figée
        # pendant cinq secondes ressemble à un plantage.
        self._en_arriere_plan(updates.derniere_publiee, suite)

    def _libelle_statut(self, statut: str) -> str:
        """Les statuts du lanceur, dits dans la langue de l'interface."""
        return self._texte(f"statut.{statut}") if f"statut.{statut}" in self.textes else statut

    def _ouvrir_historique(self) -> None:
        """Les sept derniers jours, en une table — plutôt que de fouiller le journal."""
        fenetre = tk.Toplevel(self.racine)
        fenetre.title(self._texte("histo.titre"))
        fenetre.geometry("580x320")
        cadre = ttk.Frame(fenetre, padding=10)
        cadre.pack(fill="both", expand=True)

        colonnes = ("date", "mode", "statut", "duree")
        table = ttk.Treeview(cadre, columns=colonnes, show="headings")
        for colonne, cle in zip(colonnes, ("histo.date", "histo.mode", "histo.statut",
                                           "histo.duree")):
            table.heading(colonne, text=self._texte(cle))
        table.column("date", width=180)
        table.column("mode", width=110)
        table.column("statut", width=170)
        table.column("duree", width=80, anchor="e")

        entrees = historique.recentes()
        for entree in entrees:
            try:
                duree = f"{float(entree.get('duree', 0)):.0f} s"
            except (TypeError, ValueError):
                duree = ""
            table.insert("", "end", values=(str(entree.get("date", "")).replace("T", " "),
                                            str(entree.get("mode", "")),
                                            self._libelle_statut(str(entree.get("statut", ""))),
                                            duree))
        table.pack(fill="both", expand=True)
        if not entrees:
            ttk.Label(cadre, text=self._texte("histo.vide")).pack(anchor="w", pady=(8, 0))
        ttk.Button(cadre, text=self._texte("commun.fermer"),
                   command=fenetre.destroy).pack(anchor="e", pady=(8, 0))

    def _ouvrir_diagnostic(self) -> None:
        """Le diagnostic interroge le réseau et le serveur SMTP : il tourne hors du fil UI."""
        self._afficher_statut("…")

        def travail() -> str:
            from . import doctor

            return doctor.rapport(doctor.collecter(
                dossier=self.dossier, reglages=self.reglages,
                # Relu depuis le disque, et non depuis la mémoire : c'est le seul moyen
                # d'être sûr que ce que le diagnostic affirme est bien enregistré.
                jetons=secrets.charger_jetons(paths.chemin_secret()),
                tester_smtp=mail.verifier_connexion))

        self._en_arriere_plan(travail, self._montrer_rapport)

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

    def _ouvrir_don(self) -> None:
        """Ouvre la page de soutien dans le navigateur — rien n'est transmis par l'app."""
        webbrowser.open(URL_SOUTIEN)

    def _lignes_about(self) -> list[str]:
        """Le contenu de la fenêtre « À propos ».

        La version vient du paquet, jamais d'une chaîne écrite à la main : celle-ci est restée
        bloquée sur « 1.0.0 » pendant six versions, et la fenêtre annonçait donc autre chose
        que le numéro affiché par le panneau et par le badge des versions.
        """
        verrou = {}
        try:
            import json

            verrou = json.loads((paths.dossier_executable() / "vendor" / "engine.json")
                                .read_text(encoding="utf-8"))
        except Exception:                       # noqa: BLE001 - pas de verrou : pas bloquant
            verrou = {}
        return [f"SecDailyBrief {version_actuelle}",
                f"{self._texte('about.moteur')}: {verrou.get('commit', '?')}",
                f"{self._texte('about.licence')}: MIT",
                f"{self._texte('about.depot')}: {URL_DEPOT}",
                "",
                self._texte("app.pied")]

    def _ouvrir_about(self) -> None:
        fenetre = tk.Toplevel(self.racine)
        fenetre.title(self._texte("about.titre"))
        fenetre.resizable(False, False)
        lignes = self._lignes_about()
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
