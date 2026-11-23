# SecDailyBrief

A daily security brief by e-mail, built for your own stack.

Cette application Windows pilote le moteur de veille du dépôt
[`Sec_Daily_report-`](https://github.com/Hormerty/Sec_Daily_report-) **sans le modifier** :
le moteur est récupéré à un commit épinglé, son empreinte est vérifiée, et la configuration
lui est injectée de l'extérieur.

> **État : en construction.** Aucune version distribuable pour l'instant.

## Principes

- **Rien n'est modifié chez le moteur.** `vendor/veille.py` est téléchargé à un SHA précis
  et surveillé par une empreinte ; la stack et la configuration sont injectées depuis
  l'application, avant l'appel à `main()`.
- **Aucune surveillance du poste.** L'application lit des flux publics et envoie un e-mail.
  Elle ne lit aucun document, ne capture rien, ne transmet rien à son auteur.
- **Vos réglages restent chez vous**, dans `%APPDATA%\SecDailyBrief`, et s'effacent depuis
  l'application.

## Développement

```bash
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt -r requirements-dev.txt

.venv\Scripts\python.exe tools\fetch_engine.py --sha <commit>   # récupère le moteur épinglé
.venv\Scripts\python.exe tools\fetch_engine.py --verify         # rejoue le contrôle d'empreinte

.venv\Scripts\python.exe -m pytest -q
```

### Encodage

Tout est lu et écrit en UTF-8 explicite. Deux pièges rencontrés pour de vrai, et les
parades correspondantes :

- **Windows PowerShell 5.1** — celui que Windows livre encore — lit et écrit en ANSI par
  défaut. Un aller-retour `Get-Content` / `Set-Content` sur un fichier UTF-8 le corrompt
  (`é` devient `Ã©`). On ne réécrit pas un fichier source avec ce shell : on utilise un
  éditeur, ou `-Encoding UTF8` explicitement.
- **Le BOM** — Notepad et `Out-File` en produisent un, et `json` le refuse. Le fichier de
  configuration est donc lu en `utf-8-sig`, qui l'accepte comme son absence.

Côté code, chaque `read_text` / `write_text` porte son encodage, et les sorties console
passent par `PYTHONIOENCODING=utf-8` quand elles contiennent autre chose que de l'ASCII.

## Licence

MIT — voir `LICENSE`.

Developed by Hormerty · © 2026
