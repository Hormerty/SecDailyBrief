"""Tests de la détection de fuseau : table, repli, et jamais d'écrasement d'un choix."""
from __future__ import annotations

from secdailybrief import fuseau


def test_une_zone_connue_est_traduite(monkeypatch):
    monkeypatch.setattr(fuseau, "nom_windows", lambda: "Romance Standard Time")

    assert fuseau.zone_iana() == "Europe/Paris"


def test_une_zone_inconnue_retombe_sur_le_defaut(monkeypatch):
    monkeypatch.setattr(fuseau, "nom_windows", lambda: "Zone Imaginaire Standard Time")

    assert fuseau.zone_iana() == fuseau.FUSEAU_PAR_DEFAUT


def test_absence_de_nom_retombe_sur_le_defaut(monkeypatch):
    monkeypatch.setattr(fuseau, "nom_windows", lambda: None)

    assert fuseau.zone_iana() == fuseau.FUSEAU_PAR_DEFAUT


def test_une_zone_absente_de_la_base_est_refusee(monkeypatch):
    """Si la base IANA ne connaît pas la zone, on ne la propose pas."""
    monkeypatch.setattr(fuseau, "nom_windows", lambda: "UTC")
    monkeypatch.setattr(fuseau, "_existe", lambda _zone: False)

    assert fuseau.zone_iana() == fuseau.FUSEAU_PAR_DEFAUT


def test_toutes_les_correspondances_sont_des_zones_valides():
    """Une faute de frappe dans la table donnerait un fuseau refusé au run."""
    invalides = [zone for zone in fuseau.CORRESPONDANCES.values() if not fuseau._existe(zone)]

    assert not invalides, f"zones inconnues dans la table : {invalides}"


def test_hors_windows_aucun_nom(monkeypatch):
    """Sur un système qui n'est pas Windows, la fonction ne devine pas."""
    monkeypatch.setattr(fuseau.sys, "platform", "linux")

    assert fuseau.nom_windows() is None


def test_la_detection_s_applique_a_une_premiere_execution(tmp_path, monkeypatch):
    from secdailybrief import app

    monkeypatch.setattr(app.fuseau, "zone_iana", lambda: "America/Toronto")
    monkeypatch.setenv("SECDailyBrief_DATA", str(tmp_path))

    assert app.reglages_initiaux(tmp_path)["timezone"] == "America/Toronto"


def test_un_fuseau_choisi_n_est_jamais_ecrase(tmp_path, monkeypatch):
    """Le choix de l'utilisateur prime sur toute détection."""
    from secdailybrief import app, config

    monkeypatch.setattr(app.fuseau, "zone_iana", lambda: "America/Toronto")
    monkeypatch.setenv("SECDailyBrief_DATA", str(tmp_path))
    config.enregistrer(tmp_path, {"email_user": "a@b.c", "timezone": "Asia/Tokyo"})

    assert app.reglages_initiaux(tmp_path)["timezone"] == "Asia/Tokyo"
