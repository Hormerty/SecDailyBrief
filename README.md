# SecDailyBrief

A daily security brief by e-mail, built for your own stack.

Cette application Windows pilote le moteur de veille du dépôt
[`Sec_Daily_report-`](https://github.com/Hormerty/Sec_Daily_report-) **sans le modifier** :
le moteur est récupéré à un commit épinglé, son empreinte est vérifiée, et la configuration
lui est injectée de l'extérieur.

> **Version 1.1.0** — première version distribuable, en deux archives :
> `SecDailyBrief-1.1.0-win64.zip` (données dans le profil Windows) et
> `SecDailyBrief-1.1.0-win64-portable.zip` (données à côté de l'exécutable).

## Installation

1. Téléchargez une archive depuis les [versions publiées](../../releases/latest).
2. Décompressez-la où vous voulez, puis lancez `SecDailyBrief.exe`.
3. L'assistant demande la langue, votre adresse d'envoi et un mot de passe
   d'application — pas votre mot de passe habituel. Pour Gmail :
   <https://myaccount.google.com/apppasswords>.
4. Le bouton **Tester l'envoi** vérifie la configuration avant de l'enregistrer, puis
   **Terminer** crée la tâche planifiée quotidienne.

L'exécutable n'est pas signé : Windows affichera « Windows a protégé votre PC » au premier
lancement. C'est assumé, et documenté dans le `README.txt` de l'archive.

## What it does

Chaque matin, un courriel qui rassemble les avis de sécurité du jour, note les plus
critiques, et ne garde que ce qui touche votre stack. Le moteur interroge une centaine de
sources publiques, déduplique, et rend un rapport HTML et texte.

Le programme ne tourne pas en permanence : il se réveille, travaille une à deux minutes,
puis s'arrête. Aucun compte, aucun serveur intermédiaire, aucune télémétrie.

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

### Empaqueter

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File build\build.ps1
```

Le script vérifie d'abord l'empreinte du moteur — un binaire qui embarquerait un moteur
altéré serait indétectable une fois livré — puis produit `dist\SecDailyBrief\` et **deux**
archives : `SecDailyBrief-<version>-win64.zip` et `SecDailyBrief-<version>-win64-portable.zip`.
La seconde contient un fichier `portable.flag` qui fait vivre les données dans un dossier
`data\` à côté de l'exécutable. Les deux contiennent l'exécutable, `README.txt`,
`uninstall.ps1`, `LICENSE` et `CHANGELOG.md`.

Le script refuse de construire si les trois déclarations de version divergent — le paquet,
les propriétés Windows du fichier `.exe`, et `pyproject.toml`.

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
