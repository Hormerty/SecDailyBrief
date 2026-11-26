"""Tests de la tâche planifiée : ce qui doit figurer dans le XML, et rien de plus."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
from xml.etree import ElementTree

from secdailybrief import schedule

NS = {"t": schedule.NS}


def _xml(executable=Path(r"C:\Program Files\SecDailyBrief\SecDailyBrief.exe")):
    return schedule.construire_xml(executable, heure="06:00", arguments="--run",
                                   debut=datetime(2026, 11, 24, 6, 0, 0))


def test_xml_valide_et_racine():
    racine = ElementTree.fromstring(_xml())
    assert racine.tag.endswith("Task")
    assert racine.get("version") == schedule.XML_VERSION


def test_reprise_apres_absence():
    """Le point qui compte : un PC éteint à 06:00 doit rattraper au réveil."""
    racine = ElementTree.fromstring(_xml())
    assert racine.findtext("t:Settings/t:StartWhenAvailable", namespaces=NS) == "true"


def test_relances_pendant_deux_heures():
    racine = ElementTree.fromstring(_xml())
    repetition = racine.find("t:Triggers/t:CalendarTrigger/t:Repetition", NS)
    assert repetition is not None
    assert repetition.findtext("t:Interval", namespaces=NS) == "PT15M"
    assert repetition.findtext("t:Duration", namespaces=NS) == "PT120M"


def test_heure_de_declenchement():
    racine = ElementTree.fromstring(_xml())
    debut = racine.findtext("t:Triggers/t:CalendarTrigger/t:StartBoundary", namespaces=NS)
    assert debut == "2026-11-24T06:00:00"


def test_commande_et_arguments():
    racine = ElementTree.fromstring(_xml())
    exec_ = racine.find("t:Actions/t:Exec", NS)
    commande = exec_.findtext("t:Command", namespaces=NS).strip('"')
    assert commande.endswith("SecDailyBrief.exe")
    assert exec_.findtext("t:Arguments", namespaces=NS) == "--run"


def test_chemin_avec_espaces_reste_executable():
    racine = ElementTree.fromstring(_xml())
    commande = racine.findtext("t:Actions/t:Exec/t:Command", namespaces=NS)
    assert commande.startswith('"') and commande.endswith('"')


def test_une_seule_instance_a_la_fois():
    racine = ElementTree.fromstring(_xml())
    politique = racine.findtext("t:Settings/t:MultipleInstancesPolicy", namespaces=NS)
    assert politique == "IgnoreNew"


def test_pas_de_demarrage_sur_batterie_bloque():
    racine = ElementTree.fromstring(_xml())
    assert racine.findtext(
        "t:Settings/t:DisallowStartIfOnBatteries", namespaces=NS) == "false"


# --- Alerte immédiate : seconde tâche, toutes les trois heures ------------------------------

def test_la_tache_d_alerte_se_relance_toutes_les_trois_heures():
    xml = schedule.construire_xml_alerte(Path(r"C:\Program Files\SecDailyBrief\SecDailyBrief.exe"),
                                         debut=datetime(2026, 11, 26, 9, 17))

    assert "<TimeTrigger>" in xml
    assert "<Interval>PT3H</Interval>" in xml
    assert "<Duration>P1D</Duration>" in xml
    assert "<Arguments>--alerte</Arguments>" in xml
    # Une seule instance à la fois : un passage lent ne doit pas se superposer au suivant.
    assert "<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>" in xml
    assert "2026-11-26T09:17:00" in xml


def test_la_tache_d_alerte_porte_un_nom_distinct():
    assert schedule.NOM_TACHE_ALERTE == "SecDailyBrief-Alerte"
    assert schedule.NOM_TACHE_ALERTE != schedule.NOM_TACHE
    assert schedule.HEURES_ALERTE == 3
