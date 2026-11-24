SecDailyBrief 1.1.0
===================

Un rapport de veille cybersécurité par e-mail, tous les matins, composé à partir de
sources publiques et adapté à votre stack. Aucun compte, aucune télémétrie.

Ce programme ne surveille pas votre ordinateur. Il ne lit aucun de vos documents, ne
capture rien et ne transmet rien à son auteur. Il télécharge des informations depuis des
flux publics, les résume, puis envoie le résultat à l'adresse que vous avez choisie, via
votre propre serveur de messagerie. Vos réglages restent sur ce poste et s'effacent d'un
clic.

Le programme ne tourne pas en permanence : il se réveille, travaille une à deux minutes,
puis s'arrête.


DÉMARRAGE
---------

1. Double-cliquez sur SecDailyBrief.exe.
   Windows affichera peut-être « Windows a protégé votre PC » : le programme n'est pas
   signé numériquement. Cliquez sur « Informations complémentaires » puis
   « Exécuter quand même ».

2. L'assistant demande la langue, puis votre adresse d'envoi.

3. Pour Gmail, il faut un mot de passe d'application, pas votre mot de passe habituel :
   https://myaccount.google.com/apppasswords
   Cette page n'existe que si la validation en deux étapes est active sur votre compte.

4. Le bouton « Tester l'envoi » vérifie la configuration avant d'enregistrer.

5. À la fin, une tâche planifiée est créée pour l'heure choisie (06:00 par défaut).


OÙ SONT MES DONNÉES
-------------------

Dans %APPDATA%\SecDailyBrief :

   config.json       vos réglages (adresses, heure, fuseau)
   perimetre.json    les pays et produits que vous surveillez
   secret.dpapi      le mot de passe, chiffré par Windows (illisible sur une autre machine)
   journal.log       le journal des exécutions
   historique.json   les dernières exécutions, en résumé (7 jours à l'écran)
   seen.json, stats.db, ...   l'état du moteur

Aucun de ces fichiers ne contient de mot de passe en clair. Le bouton « Supprimer toutes
mes données » du panneau efface l'ensemble d'un clic.

Le bouton « Historique » montre les sept derniers jours : date, mode, statut, durée.


MODE PORTABLE
-------------

L'archive dont le nom contient « portable » contient un fichier « portable.flag ». Tant
qu'il est là, les données vivent dans un dossier « data » à côté de l'exécutable, et non
dans votre profil Windows : le programme et vos réglages voyagent ensemble sur une clé USB.

Supprimer « portable.flag » suffit à revenir au mode normal — les données existantes, elles,
restent là où elles ont été écrites.


DÉSINSTALLATION
---------------

Lancez uninstall.ps1 (clic droit → « Exécuter avec PowerShell »). Il retire la tâche
planifiée et propose de supprimer les données. Vous pouvez ensuite effacer ce dossier.


EN CAS DE PROBLÈME
------------------

Le bouton « Diagnostic » du panneau produit un rapport : dix vérifications (moteur,
dépendances, certificats TLS, dossier, configuration, mot de passe, fuseau, réseau, SMTP,
tâche planifiée). Copiez-le dans votre demande d'aide, il évite beaucoup d'allers-retours.

Le journal complet se lit aussi dans le panneau, bouton « Journal ».


LICENCE
-------

MIT — voir LICENSE. Logiciel fourni sans garantie.

Développé par Hormerty · © 2026
