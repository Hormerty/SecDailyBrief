# Journal des versions

## 1.1.0 — 24 novembre 2026

### Ajouté

- **Mode portable** : une seconde archive, marquée `portable.flag`, dont les données vivent
  dans un dossier `data` à côté de l'exécutable au lieu du profil Windows. Le diagnostic
  indique le mode en cours, parce que la différence compte : en portable, effacer le dossier
  efface aussi les réglages.
- **Historique des sept derniers jours**, accessible depuis le panneau : date, mode, statut
  et durée de chaque exécution, sans avoir à fouiller le journal.
- **Validation stricte du fichier de périmètre** à l'ouverture. La section fautive est nommée
  — section inconnue, `stack` en liste, mots-clés vides — et les valeurs d'exemple peuvent
  être rétablies. Le fichier fautif est conservé sous `.invalide` plutôt que détruit.
- Les statuts d'exécution sont traduits dans la ligne d'état et dans l'historique.

### Modifié

- **La version est vérifiée à la construction** : le paquet, les propriétés Windows et
  `pyproject.toml` doivent dire la même chose, sinon la construction s'arrête. Trois copies
  d'une même vérité finissent toujours par diverger.
- Le bouton « Faire un don » est en graisse normale, comme les autres.

### Corrigé

- Le réglage du consentement n'est plus redemandé à chaque retour sur la page.

## 1.0.0 — 23 novembre 2026

Première version utilisable.

- Assistant en cinq pages : langue (FR/EN/NL), consentement, compte d'envoi, stack, planning.
- Panneau de contrôle : lancer, aperçu, ouvrir le rapport, tester les sources, vérifier les
  liens, journal, diagnostic, historique.
- Envoi vérifié par un vrai message avant enregistrement ; mot de passe chiffré par Windows.
- Tâche planifiée quotidienne, avec rattrapage si la machine était éteinte.
- Diagnostic en dix points, dont l'importabilité réelle du moteur et la présence des
  certificats TLS.
- Moteur embarqué à un commit épinglé, avec empreinte vérifiée à chaque construction.
