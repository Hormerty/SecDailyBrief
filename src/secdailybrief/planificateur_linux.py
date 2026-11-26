"""Génération des unités systemd (mode utilisateur) à partir du même XML que Windows.

Le XML reste la description unique des deux tâches : le convertir en unités évite de faire
diverger les deux planificateurs, et laisse `app.py` appeler la même fonction des deux côtés.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from xml.etree import ElementTree

NS = "{http://schemas.microsoft.com/windows/2004/02/mit/task}"


def _dossier_unites() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "systemd" / "user"


def unites(xml: str, nom: str) -> tuple[str, str]:
    """(service, timer) déduits du XML de tâche.

    Deux déclencheurs possibles, ceux que produisent `construire_xml` : quotidien avec heure,
    ou relance périodique (`Repetition/Interval`) pour la tâche d'alerte.
    """
    racine = ElementTree.fromstring(xml)
    execution = racine.find(f"{NS}Actions/{NS}Exec")
    commande = (execution.findtext(f"{NS}Command") or "").strip().strip('"')
    arguments = (execution.findtext(f"{NS}Arguments") or "").strip()
    description = (racine.findtext(f"{NS}RegistrationInfo/{NS}Description")
                   or nom).strip()
    debut = (racine.findtext(f"{NS}Triggers/{NS}CalendarTrigger/{NS}StartBoundary")
             or racine.findtext(f"{NS}Triggers/{NS}TimeTrigger/{NS}StartBoundary") or "")
    repetition = (
        racine.findtext(f"{NS}Triggers/{NS}CalendarTrigger/{NS}Repetition/{NS}Interval")
        or racine.findtext(f"{NS}Triggers/{NS}TimeTrigger/{NS}Repetition/{NS}Interval") or "")
    # La tâche quotidienne porte elle aussi une `Repetition` (PT15M pendant deux heures) :
    # c'est la fenêtre de reprise de Windows, pas la cadence. Seul un `TimeTrigger` décrit une
    # relance périodique ; `ScheduleByDay` reste un rendez-vous quotidien, et c'est
    # `Persistent=true` qui rattrape une exécution manquée.
    periodique = racine.find(f"{NS}Triggers/{NS}TimeTrigger") is not None

    if periodique and repetition.endswith("H"):
        # Relance périodique : OnUnitActiveSec repart après chaque exécution, ce qui évite
        # les rafales quand la machine se réveille après une longue veille. systemd veut une
        # durée (« 3h »), pas la forme ISO du XML (« PT3H »).
        duree = "3h"
        chiffres = repetition[2:-1] if repetition.startswith("PT") else repetition[:-1]
        if chiffres.isdigit():
            duree = f"{chiffres}h"
        cadence = f"OnBootSec=5min\nOnUnitActiveSec={duree}"
    else:
        heure = debut[11:16] if len(debut) >= 16 else "06:00"
        cadence = f"OnCalendar=*-*-* {heure}:00\nPersistent=true"

    service = f"""[Unit]
Description={description}

[Service]
Type=oneshot
ExecStart="{commande}" {arguments}
"""
    timer = f"""[Unit]
Description={description}

[Timer]
{cadence}

[Install]
WantedBy=timers.target
"""
    return service, timer


def _systemctl(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run(["systemctl", "--user", *arguments], capture_output=True,
                          text=True, check=False)


def installer(xml: str, nom: str) -> None:
    """Écrit les unités, recharge systemd et active le timer."""
    service, timer = unites(xml, nom)
    dossier = _dossier_unites()
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / f"{nom}.service").write_text(service, encoding="utf-8")
    (dossier / f"{nom}.timer").write_text(timer, encoding="utf-8")
    _systemctl("daemon-reload")
    resultat = _systemctl("enable", "--now", f"{nom}.timer")
    if resultat.returncode != 0:
        raise OSError(f"activation du timer impossible : {resultat.stderr or resultat.stdout}")


def existe(nom: str) -> bool:
    if not (_dossier_unites() / f"{nom}.timer").exists():
        return False
    return _systemctl("is-enabled", f"{nom}.timer").returncode == 0


def supprimer(nom: str) -> None:
    _systemctl("disable", "--now", f"{nom}.timer")
    for suffixe in (".timer", ".service"):
        (_dossier_unites() / f"{nom}{suffixe}").unlink(missing_ok=True)
    _systemctl("daemon-reload")


def prochaine_execution(nom: str) -> str | None:
    resultat = _systemctl("show", f"{nom}.timer", "-p", "NextElapseUSecRealtime", "--value")
    valeur = (resultat.stdout or "").strip()
    return valeur or None


def est_systemd() -> bool:
    return sys.platform != "win32"
