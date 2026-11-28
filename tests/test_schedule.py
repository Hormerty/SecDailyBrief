"""Tests de la tâche planifiée : ce qui doit figurer dans le XML, et rien de plus."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree

from secdailybrief import planificateur_linux, schedule

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
    # Ce test verifiait la borne qui tuait la tache au bout d'un jour. Mesure du 28/11/2026 :
    # avec une duree, le Planificateur affiche « Prochaine execution : N/A » apres la serie.
    assert "<Duration>" not in xml
    assert "<Arguments>--alerte</Arguments>" in xml
    # Une seule instance à la fois : un passage lent ne doit pas se superposer au suivant.
    assert "<MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>" in xml
    assert "2026-11-26T09:17:00" in xml


def test_la_tache_d_alerte_porte_un_nom_distinct():
    assert schedule.NOM_TACHE_ALERTE == "SecDailyBrief-Alerte"
    assert schedule.NOM_TACHE_ALERTE != schedule.NOM_TACHE
    assert schedule.HEURES_ALERTE == 3


# --- Planificateur Linux : unités systemd --------------------------------------------------

def test_la_tache_quotidienne_devient_un_timer_quotidien():
    """Le XML quotidien porte aussi une Repetition (PT15M) : c'est la reprise Windows, pas
    la cadence. systemd doit voir un rendez-vous à 06:00, pas une relance toutes les 15 min."""
    xml = schedule.construire_xml(PurePosixPath("/opt/SecDailyBrief/SecDailyBrief"),
                                  heure="06:00", arguments="--run")

    service, timer = planificateur_linux.unites(xml, "SecDailyBrief")

    assert "OnCalendar=*-*-* 06:00:00" in timer
    assert "Persistent=true" in timer
    assert "PT15M" not in timer
    assert 'ExecStart="/opt/SecDailyBrief/SecDailyBrief" --run' in service


def test_la_tache_d_alerte_devient_une_relance_de_trois_heures():
    xml = schedule.construire_xml_alerte(PurePosixPath("/opt/SecDailyBrief/SecDailyBrief"),
                                         arguments="--alerte")

    service, timer = planificateur_linux.unites(xml, "SecDailyBrief-Alerte")

    assert "OnUnitActiveSec=3h" in timer
    assert "OnBootSec=5min" in timer
    assert "--alerte" in service


def test_les_unites_s_inspectent_sans_systemd():
    """La génération est pure : elle doit être vérifiable depuis Windows comme depuis Linux."""
    xml = schedule.construire_xml(PurePosixPath("/opt/SecDailyBrief/SecDailyBrief"), heure="07:30")

    _, timer = planificateur_linux.unites(xml, "Tache")

    assert "OnCalendar=*-*-* 07:30:00" in timer
    assert "[Install]" in timer and "WantedBy=timers.target" in timer


def test_la_tache_d_alerte_ne_borne_pas_sa_repetition():
    """Mesure du 28/11/2026 : avec une durée d'un jour, la tâche s'arrêtait après 8 exécutions.

    Un TimeTrigger ne se déclenche qu'une fois ; sa durée borne donc la seule série qu'il lancera
    jamais, et le Planificateur affichait ensuite « Prochaine exécution : N/A ».
    """
    from pathlib import Path

    from secdailybrief import schedule

    xml = schedule.construire_xml_alerte(Path("SecDailyBrief.exe"))

    assert "<TimeTrigger>" in xml
    assert "<Duration>" not in xml            # sinon la répétition meurt au bout d'un jour
    assert "<StopAtDurationEnd>" not in xml
    assert "<Interval>PT%dH</Interval>" % schedule.HEURES_ALERTE in xml


def test_la_tache_quotidienne_garde_sa_fenetre_de_reprise():
    """Elle, au contraire, doit borner sa reprise : un CalendarTrigger la relance chaque jour."""
    from pathlib import Path

    from secdailybrief import schedule

    xml = schedule.construire_xml(Path("SecDailyBrief.exe"), heure="07:00")

    assert "<CalendarTrigger>" in xml
    assert "<Duration>" in xml                # la fenêtre de reprise de 2 h
    assert "<ScheduleByDay>" in xml           # et le déclenchement quotidien qui la renouvelle

def test_l_heure_du_declencheur_est_celle_de_la_machine():
    """Le fuseau choisi ne deplace pas le declencheur : il decide de la journee du moteur.

    Windows ne connait que l'heure locale du poste. Ce test fige cette semantique : si un jour
    l'heure etait convertie depuis le fuseau choisi, il rougirait, et la decision serait alors
    explicite plutot que silencieuse.
    """
    from datetime import datetime

    from secdailybrief import schedule

    xml = schedule.construire_xml(Path("SecDailyBrief.exe"), heure="07:00")
    attendu = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)

    assert f"<StartBoundary>{attendu:%Y-%m-%dT%H:%M:%S}</StartBoundary>" in xml
