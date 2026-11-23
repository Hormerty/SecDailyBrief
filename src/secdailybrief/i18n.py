"""Textes de l'interface, en français et en anglais.

Deux langues sont livrées ; les autres s'ajoutent en déposant un dictionnaire ici, sans
toucher au reste du code. Une clé absente retombe sur l'anglais plutôt que d'afficher un
identifiant technique — un utilisateur ne doit jamais voir « wizard.email.label ».

Les noms propres et les mentions légales ne sont pas traduits : « Developed by Hormerty »
reste en anglais, comme la fenêtre About, par choix.
"""
from __future__ import annotations

LANGUE_PAR_DEFAUT = "en"

TEXTES: dict[str, dict[str, str]] = {
    "fr": {
        "app.titre": "SecDailyBrief",
        "app.pied": "Developed by Hormerty · © 2026",
        "wizard.bienvenue": "Bienvenue dans SecDailyBrief",
        "wizard.intro": "Ce programme envoie chaque matin un rapport de veille sécurité, "
                        "composé à partir de sources publiques, à l'adresse de votre choix.",
        "wizard.langue": "Langue de l'interface",
        "wizard.suivant": "Suivant",
        "wizard.precedent": "Précédent",
        "wizard.terminer": "Terminer",
        "consent.titre": "Ce que fait ce programme",
        "consent.texte": "Il ne surveille pas votre ordinateur. Il ne lit aucun de vos "
                         "documents, ne capture rien et ne transmet rien à son auteur. Il "
                         "télécharge des informations depuis des flux publics, les résume, "
                         "puis envoie le résultat à l'adresse que vous avez choisie, via "
                         "votre propre serveur de messagerie. Vos réglages restent sur ce "
                         "poste et s'effacent d'un clic.",
        "consent.domaines": "Domaines contactés",
        "consent.accepte": "J'ai compris ce que fait ce programme",
        "consent.pause": "Le programme ne tourne pas en permanence : il se réveille, "
                         "travaille une à deux minutes, puis s'arrête.",
        "courriel.titre": "Votre messagerie",
        "courriel.expediteur": "Adresse d'envoi",
        "courriel.destinataire": "Adresse de réception",
        "courriel.meme": "Recevoir à la même adresse",
        "courriel.motdepasse": "Mot de passe d'application",
        "courriel.aide": "Gmail exige un mot de passe d'application, pas votre mot de "
                         "passe habituel. Il n'existe que si la validation en deux étapes "
                         "est activée.",
        "courriel.lien": "Créer un mot de passe d'application",
        "courriel.tester": "Tester l'envoi",
        "courriel.test.ok": "Test réussi : le message est parti.",
        "courriel.test.echec": "Le test a échoué. Vérifiez l'adresse et le mot de passe.",
        "courriel.outlook": "Outlook exige une authentification moderne, prévue pour la "
                            "version 2. Utilisez pour l'instant un autre fournisseur.",
        "stack.titre": "Votre stack",
        "stack.explication": "Les produits que vous surveillez. La liste proposée est "
                             "celle de l'auteur, à titre d'exemple — remplacez-la.",
        "stack.ajouter": "Ajouter un produit",
        "stack.nom": "Nom affiché",
        "stack.mots": "Locutions (séparées par des virgules)",
        "secrets.titre": "Réglages avancés",
        "secrets.nvd": "Clé NVD (facultative) — 30 analyses au lieu de 10",
        "secrets.ransomware": "Clé Ransomware.live (facultative)",
        "secrets.github": "Jeton GitHub en lecture seule (facultatif)",
        "planif.titre": "Planification",
        "planif.heure": "Heure d'envoi",
        "planif.fenetre": "Fenêtre de collecte (heures)",
        "planif.fuseau": "Fuseau horaire",
        "panneau.statut": "Dernière exécution",
        "panneau.jamais": "Aucune exécution pour l'instant.",
        "panneau.lancer": "Lancer maintenant",
        "panneau.apercu": "Voir un aperçu",
        "panneau.rapport": "Ouvrir le dernier rapport",
        "panneau.journal": "Journal",
        "panneau.sources": "Tester les sources",
        "panneau.liens": "Vérifier les liens",
        "panneau.prochaine": "Prochaine exécution",
        "panneau.reglages": "Réglages",
        "panneau.effacer": "Supprimer toutes mes données",
        "panneau.effacer.confirme": "Configuration, mot de passe et état seront supprimés.",
        "about.titre": "About",
        "about.version": "Version",
        "about.moteur": "Engine",
        "about.licence": "License",
        "about.depot": "Repository",
        "commun.oui": "Oui",
        "commun.non": "Non",
        "commun.annuler": "Annuler",
        "commun.enregistrer": "Enregistrer",
        "commun.erreur": "Erreur",
    },
    "en": {
        "app.titre": "SecDailyBrief",
        "app.pied": "Developed by Hormerty · © 2026",
        "wizard.bienvenue": "Welcome to SecDailyBrief",
        "wizard.intro": "This program sends a security watch report every morning, built "
                        "from public sources, to the address of your choice.",
        "wizard.langue": "Interface language",
        "wizard.suivant": "Next",
        "wizard.precedent": "Back",
        "wizard.terminer": "Finish",
        "consent.titre": "What this program does",
        "consent.texte": "It does not monitor your computer. It reads none of your "
                         "documents, captures nothing and sends nothing to its author. It "
                         "downloads information from public feeds, summarises it, and sends "
                         "the result to the address you chose, through your own mail "
                         "server. Your settings stay on this machine and are erased in one "
                         "click.",
        "consent.domaines": "Domains contacted",
        "consent.accepte": "I understand what this program does",
        "consent.pause": "The program does not run continuously: it wakes up, works for a "
                         "minute or two, then stops.",
        "courriel.titre": "Your mail account",
        "courriel.expediteur": "Sender address",
        "courriel.destinataire": "Recipient address",
        "courriel.meme": "Receive at the same address",
        "courriel.motdepasse": "App password",
        "courriel.aide": "Gmail requires an app password, not your usual one. It only "
                         "exists if two-step verification is enabled.",
        "courriel.lien": "Create an app password",
        "courriel.tester": "Test sending",
        "courriel.test.ok": "Test passed: the message was sent.",
        "courriel.test.echec": "The test failed. Check the address and the password.",
        "courriel.outlook": "Outlook requires modern authentication, planned for version 2. "
                            "Use another provider for now.",
        "stack.titre": "Your stack",
        "stack.explication": "The products you watch. The proposed list is the author's, as "
                             "an example — replace it.",
        "stack.ajouter": "Add a product",
        "stack.nom": "Display name",
        "stack.mots": "Phrases (comma separated)",
        "secrets.titre": "Advanced settings",
        "secrets.nvd": "NVD key (optional) — 30 lookups instead of 10",
        "secrets.ransomware": "Ransomware.live key (optional)",
        "secrets.github": "Read-only GitHub token (optional)",
        "planif.titre": "Schedule",
        "planif.heure": "Sending time",
        "planif.fenetre": "Collection window (hours)",
        "planif.fuseau": "Time zone",
        "panneau.statut": "Last run",
        "panneau.jamais": "No run yet.",
        "panneau.lancer": "Run now",
        "panneau.apercu": "Preview",
        "panneau.rapport": "Open last report",
        "panneau.journal": "Log",
        "panneau.sources": "Test sources",
        "panneau.liens": "Check links",
        "panneau.prochaine": "Next run",
        "panneau.reglages": "Settings",
        "panneau.effacer": "Delete all my data",
        "panneau.effacer.confirme": "Configuration, password and state will be removed.",
        "about.titre": "About",
        "about.version": "Version",
        "about.moteur": "Engine",
        "about.licence": "License",
        "about.depot": "Repository",
        "commun.oui": "Yes",
        "commun.non": "No",
        "commun.annuler": "Cancel",
        "commun.enregistrer": "Save",
        "commun.erreur": "Error",
    },
}


def langues_proposees() -> list[str]:
    """Langues réellement disponibles, triées : on n'annonce pas une langue sans textes."""
    return sorted(TEXTES)


def textes(code: str | None) -> dict[str, str]:
    """Dictionnaire de la langue demandée, complété par l'anglais pour les clés manquantes."""
    base = dict(TEXTES[LANGUE_PAR_DEFAUT])
    if code and code in TEXTES:
        base.update(TEXTES[code])
    return base


def apparier_langue_systeme(code_systeme: str | None) -> str:
    """« fr-BE » → « fr » ; langue inconnue → anglais."""
    court = (code_systeme or "")[:2].lower()
    return court if court in TEXTES else LANGUE_PAR_DEFAUT
