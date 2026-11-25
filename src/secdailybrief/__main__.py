"""Point d'entrée : interface graphique, exécution, ou moteur embarqué.

Trois modes, et une règle : **le mode par défaut ouvre l'interface**. Une tâche planifiée
appelle `--run`, l'aperçu `--preview`, et le mode `--moteur` n'existe que pour
l'exécutable figé, qui n'a pas d'interpréteur Python séparé à relancer.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import config as configuration
from . import engine, logging_setup, paths, runner, secrets


def executer_moteur() -> int:
    """Exécute le moteur dans le processus courant (chemin de l'exécutable figé).

    Toute exception est journalisée et transformée en code de sortie : sans ça, une erreur
    du moteur fait apparaître la boîte « Unhandled exception in script » de PyInstaller, qui
    ne dit rien d'utile à l'utilisateur et ferme l'application.
    """
    journal = logging_setup.journaliser(paths.chemin_journal())
    try:
        return engine.module().main()
    except Exception as exc:      # noqa: BLE001 - on rapporte, on ne laisse pas mourir
        journal.exception("Echec du moteur : %s", exc)
        return 1


def _executer(mode: str) -> int:
    dossier = paths.s_assurer_dossier()
    journal = logging_setup.journaliser(paths.chemin_journal())
    reglages = configuration.charger(dossier)

    problemes = configuration.valider(reglages)
    if problemes:
        journal.error("Configuration incomplete : %s", ", ".join(problemes))
        return 2

    jetons = secrets.charger_jetons(paths.chemin_secret())
    mot_de_passe = jetons.get("smtp_password", "")
    if not mot_de_passe:
        journal.error("Aucun mot de passe enregistre : ouvrez l'interface et enregistrez-le.")
        return 2

    resultat = runner.executer(reglages, mot_de_passe, journal, mode=mode, dossier=dossier)
    return 0 if resultat.statut == "ok" else 1


def _signaler(erreur: Exception) -> None:
    """Dit à l'utilisateur que l'application s'est arrêtée, sans lui montrer une trace.

    PyInstaller affiche sinon sa propre boîte « Unhandled exception in script », qui aligne
    trente lignes de frames et se termine par un chemin interne — illisible pour qui voulait
    juste lancer un rapport.
    """
    message = (
        "SecDailyBrief s'est arrete sur une erreur inattendue.\n\n"
        f"{type(erreur).__name__} : {erreur}\n\n"
        f"Le detail est dans le journal :\n{paths.chemin_journal()}"
    )
    try:
        import tkinter as tk
        from tkinter import messagebox

        racine = tk.Tk()
        racine.withdraw()
        messagebox.showerror("SecDailyBrief", message)
        racine.destroy()
    except Exception:            # noqa: BLE001 - pas d'affichage : la console suffira
        print(message, file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    try:
        return _main(argv)
    except SystemExit:
        raise
    except Exception as exc:     # noqa: BLE001 - filet global : rien ne doit sortir en trace
        try:
            logging_setup.journaliser(paths.chemin_journal()).exception(
                "Echec inattendu : %s", exc)
        except Exception:        # noqa: BLE001 - journaliser ne doit pas masquer l'erreur
            pass
        _signaler(exc)
        return 1


def _main(argv: list[str] | None = None) -> int:
    parseur = argparse.ArgumentParser(prog="SecDailyBrief", add_help=True)
    parseur.add_argument("--run", action="store_true", help="executer la veille et envoyer")
    parseur.add_argument("--preview", action="store_true", help="ecrire un apercu sans envoyer")
    parseur.add_argument("--moteur", action="store_true", help=argparse.SUPPRESS)
    parseur.add_argument("--doctor", action="store_true", help="diagnostic complet")
    arguments = parseur.parse_args(argv)

    if arguments.moteur:
        return executer_moteur()
    if arguments.doctor:
        from . import doctor

        return doctor.executer()
    if arguments.preview:
        return _executer("preview")
    if arguments.run:
        return _executer("run")

    from . import app  # interface : importée seulement si on en a besoin

    return app.lancer()


if __name__ == "__main__":
    raise SystemExit(main())
