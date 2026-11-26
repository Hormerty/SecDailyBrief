"""Inscription dans le Planificateur de tâches de Windows.

La tâche n'est pas créée par `schtasks /Create /SC DAILY` mais par un XML complet, pour
deux raisons qu'aucune option de ligne de commande ne couvre :

* **StartWhenAvailable** : si le PC était éteint à 06:00, la tâche se déclenche au premier
  réveil. Sans ça, un portable fermé le matin ne produit aucun rapport.
* **Repetition** : une relance toutes les 15 minutes pendant deux heures. C'est la fenêtre
  de reprise qui rattrape un réseau pas encore monté au réveil ; le garde-fou « un seul
  rapport par jour » du moteur rend ces relances inoffensives.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

NOM_TACHE = "SecDailyBrief"
NOM_TACHE_ALERTE = "SecDailyBrief-Alerte"
HEURES_ALERTE = 3   # même cadence que le workflow `alerte.yml` du dépôt du moteur
XML_VERSION = "1.2"
NS = "http://schemas.microsoft.com/windows/2004/02/mit/task"
DECLARATION = '<?xml version="1.0" encoding="UTF-16"?>\n'
DRAPEAUX = 0x08000000  # CREATE_NO_WINDOW : pas de console qui clignote


def construire_xml(executable: Path, heure: str = "06:00", arguments: str = "--run",
                   repetition_minutes: int = 15, duree_reprise_minutes: int = 120,
                   debut: datetime | None = None) -> str:
    """Corps XML de la tâche quotidienne, avec reprise et relances.

    La déclaration `<?xml …?>` n'est pas incluse : elle est ajoutée à l'écriture, avec
    l'encodage réellement utilisé par le fichier. Une déclaration qui ne correspond pas à
    l'encodage du fichier est refusée par le Planificateur, et c'est exactement l'erreur
    qu'on a eue la première fois.
    """
    debut = debut or datetime.now().replace(hour=int(heure.split(":")[0]),
                                            minute=int(heure.split(":")[1]),
                                            second=0, microsecond=0)
    return f"""<Task version="{XML_VERSION}" xmlns="{NS}">
  <RegistrationInfo>
    <Description>SecDailyBrief - rapport de veille quotidien</Description>
  </RegistrationInfo>
  <Triggers>
    <CalendarTrigger>
      <StartBoundary>{debut:%Y-%m-%dT%H:%M:%S}</StartBoundary>
      <Enabled>true</Enabled>
      <ScheduleByDay>
        <DaysInterval>1</DaysInterval>
      </ScheduleByDay>
      <Repetition>
        <Interval>PT{repetition_minutes}M</Interval>
        <Duration>PT{duree_reprise_minutes}M</Duration>
        <StopAtDurationEnd>true</StopAtDurationEnd>
      </Repetition>
    </CalendarTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT20M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{executable}"</Command>
      <Arguments>{arguments}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def construire_xml_alerte(executable: Path, heures: int = HEURES_ALERTE,
                          arguments: str = "--alerte",
                          debut: datetime | None = None) -> str:
    """Corps XML de la tâche d'alerte immédiate, relancée toutes les `heures`.

    Distincte de la tâche quotidienne : celle-ci porte un rapport à 06:00 avec une fenêtre de
    reprise, celle-là tourne en boucle et n'écrit que si une faille dépasse le seuil d'alerte.
    `MultipleInstancesPolicy` à IgnoreNew évite qu'un passage lent se superpose au suivant.
    """
    debut = debut or datetime.now().replace(minute=17, second=0, microsecond=0)
    return f"""<Task version="{XML_VERSION}" xmlns="{NS}">
  <RegistrationInfo>
    <Description>SecDailyBrief - alerte immediate toutes les {heures} heures</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{debut:%Y-%m-%dT%H:%M:%S}</StartBoundary>
      <Enabled>true</Enabled>
      <Repetition>
        <Interval>PT{heures}H</Interval>
        <Duration>P1D</Duration>
        <StopAtDurationEnd>true</StopAtDurationEnd>
      </Repetition>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>true</RunOnlyIfNetworkAvailable>
    <ExecutionTimeLimit>PT20M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>"{executable}"</Command>
      <Arguments>{arguments}</Arguments>
    </Exec>
  </Actions>
</Task>
"""


def _schtasks(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["schtasks", *arguments], capture_output=True, text=True,
                          creationflags=DRAPEAUX, check=False)


def _linux():
    from . import planificateur_linux
    return planificateur_linux


def installer(xml: str, nom: str = NOM_TACHE) -> None:
    """Crée ou remplace la tâche : schtasks sous Windows, unités systemd ailleurs.

    Le XML reste la description commune ; le planificateur Linux le convertit plutôt que de
    maintenir deux définitions qui divergeraient.
    """
    if sys.platform != "win32":
        return _linux().installer(xml, nom)
    with tempfile.NamedTemporaryFile("w", suffix=".xml", encoding="utf-16",
                                     delete=False) as fichier:
        fichier.write(DECLARATION + xml)
        chemin = fichier.name
    try:
        resultat = _schtasks("/Create", "/TN", nom, "/XML", chemin, "/F")
    finally:
        Path(chemin).unlink(missing_ok=True)
    if resultat.returncode != 0:
        raise OSError(f"creation de la tache impossible : {resultat.stderr or resultat.stdout}")


def supprimer(nom: str = NOM_TACHE) -> None:
    if sys.platform != "win32":
        return _linux().supprimer(nom)
    _schtasks("/Delete", "/TN", nom, "/F")


def existe(nom: str = NOM_TACHE) -> bool:
    if sys.platform != "win32":
        return _linux().existe(nom)
    return _schtasks("/Query", "/TN", nom).returncode == 0


def prochaine_execution(nom: str = NOM_TACHE) -> str | None:
    """Prochaine exécution, lue par PowerShell pour ne pas dépendre de la langue du système.

    `schtasks /Query` renvoie des libellés traduits (« Prochaine exécution » en français) :
    les analyser serait fragile. Les propriétés PowerShell, elles, ne changent pas.
    """
    commande = ["powershell", "-NoProfile", "-NonInteractive", "-Command",
                f"(Get-ScheduledTaskInfo -TaskName '{nom}').NextRunTime.ToString('o')"]
    resultat = subprocess.run(commande, capture_output=True, text=True,
                              creationflags=DRAPEAUX, check=False)
    if resultat.returncode != 0 or not resultat.stdout.strip():
        return None
    return resultat.stdout.strip()
