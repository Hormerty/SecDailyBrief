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
import re
import threading
import tkinter as tk
import webbrowser
from pathlib import Path
from tkinter import messagebox, ttk

from . import config as configuration
from . import engine, i18n, logging_setup, mail, paths, runner, schedule, secrets

TAILLE_MIN = (760, 540)
URL_MOT_DE_PASSE = "https://myaccount.google.com/apppasswords"
URL_DEPOT = "https://github.com/Hormerty/Sec_Daily_report-"
NBSP = "\u00a0"


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

        self.racine.title(self.textes["app.titre"])
        self.racine.minsize(*TAILLE_MIN)
        self.racine.protocol("WM_DELETE_WINDOW", self.racine.destroy)
        self.racine.bind("<Escape>", lambda _event: self.racine.destroy())

        self.corps = ttk.Frame(self.racine, padding=16)
        self.corps.pack(side="top", fill="both", expand=True)

        # Le pied est posé en dernier sur le bas : il reste visible même si la fenêtre est
        # réduite, et il ne dépend pas de la page affichée.
        self.pied = ttk.Label(self.racine, text=self.textes["app.pied"], anchor="w",
                              padding=(12, 6), relief="groove")
        self.pied.pack(side="bottom", fill="x")

        if self.reglages.get("email_user"):
            self.afficher_panneau()
        else:
            self.page_langue()

    # --- utilitaires -------------------------------------------------------
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
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
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
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")
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
        ttk.Checkbutton(page, text=self._texte("consent.titre"), variable=self.consentement
                        ).pack(anchor="w", pady=(8, 0))

        barre = ttk.Frame(page)
        barre.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(barre, text=self._texte("wizard.precedent"),
                   command=self.page_langue).pack(side="left")
        ttk.Button(barre, text=self._texte("wizard.suivant"),
                   command=self.page_courriel).pack(side="right")

    def page_courriel(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        ttk.Label(page, text=self._texte("courriel.titre"),
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")

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
                   command=self.page_stack).pack(side="right")

    def _synchroniser_adresses(self) -> None:
        if self.var_meme.get():
            self.var_destinataire.set(self.var_expediteur.get())

    def _collecter_courriel(self) -> bool:
        expediteur = self.var_expediteur.get().strip()
        destinataire = self.var_destinataire.get().strip() or expediteur
        self.brouillon["email_user"] = expediteur
        self.brouillon["recipient_email"] = destinataire
        if expediteur.lower().endswith(("@outlook.com", "@hotmail.com", "@live.com",
                                        "@outlook.fr", "@hotmail.fr")):
            messagebox.showinfo(self._texte("commun.erreur"), self._texte("courriel.outlook"))
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

        ttk.Label(page, text=self._texte("stack.titre"),
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(page, text=self._texte("stack.explication"), wraplength=690,
                  justify="left").pack(anchor="w", pady=(6, 10))

        cadre = ttk.Frame(page)
        cadre.pack(fill="both", expand=True)
        self.arbre = ttk.Treeview(cadre, columns=("mots",), show="tree headings", height=8)
        self.arbre.heading("#0", text=self._texte("stack.nom"))
        self.arbre.heading("mots", text=self._texte("stack.mots"))
        self.arbre.column("#0", width=200)
        self.arbre.pack(side="left", fill="both", expand=True)
        ttk.Scrollbar(cadre, orient="vertical", command=self.arbre.yview).pack(side="right",
                                                                              fill="y")
        self._remplir_stack()

        barre = ttk.Frame(page)
        barre.pack(side="bottom", fill="x", pady=(16, 0))
        ttk.Button(barre, text=self._texte("wizard.precedent"),
                   command=self.page_courriel).pack(side="left")
        ttk.Button(barre, text=self._texte("wizard.suivant"),
                   command=self.page_planification).pack(side="right")

    def _remplir_stack(self) -> None:
        for item in self.arbre.get_children():
            self.arbre.delete(item)
        stack = self.perimetre.get("stack") or {}
        if not stack:
            try:
                stack = engine.stack_par_defaut(self.dossier)
            except Exception:                   # noqa: BLE001 - moteur absent : liste vide
                stack = {}
        for nom, mots in stack.items():
            self.arbre.insert("", "end", text=nom, values=(", ".join(mots),))

    def page_planification(self) -> None:
        page = self._vider()
        page.pack(fill="both", expand=True)

        ttk.Label(page, text=self._texte("planif.titre"),
                  font=("Segoe UI", 14, "bold")).pack(anchor="w")

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
        ttk.Entry(cadre, textvariable=self.var_fuseau, width=32).grid(row=2, column=1,
                                                                      sticky="w")

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
                  font=("Segoe UI", 16, "bold")).pack(anchor="w")
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

        bas = ttk.Frame(page)
        bas.pack(side="bottom", fill="x")
        ttk.Button(bas, text=self._texte("panneau.effacer"),
                   command=self._effacer_donnees).pack(side="right")
        ttk.Button(bas, text=self._texte("about.titre"),
                   command=self._ouvrir_about).pack(side="left")

    def _afficher_prochaine(self) -> None:
        try:
            prochaine = schedule.prochaine_execution()
        except Exception:                       # noqa: BLE001 - pas de tâche : rien à dire
            prochaine = None
        if prochaine:
            self.var_prochaine.set(f"{self._texte('panneau.prochaine')} : {prochaine[:19]}")

    def _afficher_statut(self, texte: str) -> None:
        self.var_statut.set(texte)

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
