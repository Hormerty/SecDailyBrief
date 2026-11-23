"""Vérifie que le moteur épinglé expose encore tout ce dont l'application dépend.

C'est le prix de l'épinglage : l'application injecte sa configuration dans veille.py de
l'extérieur — elle réaffecte STACK_PRODUCTS puis reconstruit RE_STACK avec _pattern().
Un renommage côté moteur casserait donc l'application sans casser le moteur. Ici, la
casse se produit à la compilation, pas chez un utilisateur.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

RACINE = Path(__file__).resolve().parent.parent
VENDOR = RACINE / "vendor"
sys.path.insert(0, str(VENDOR))

import veille  # noqa: E402  (import après l'ajout du chemin)


def test_moteur_present_et_verrouille():
    verrou = json.loads((VENDOR / "engine.json").read_text(encoding="utf-8"))
    assert verrou["commit"], "le verrou doit citer le commit épinglé"
    assert verrou["sha256"], "le verrou doit citer l'empreinte"
    assert Path(veille.__file__).resolve() == (VENDOR / "veille.py").resolve()


def test_points_accroche_utilises_par_l_application():
    for nom in ("STACK_PRODUCTS", "RE_STACK", "_pattern", "detect_stack",
                "main", "validate_config", "render_html", "send_email"):
        assert hasattr(veille, nom), f"le moteur n'expose plus {nom}"
    assert isinstance(veille.STACK_PRODUCTS, dict)


def test_degrade_et_apercu_disponibles():
    assert callable(veille.degradation_reason)
    assert callable(veille._preview_state)
    assert hasattr(veille, "PREVIEW")
    assert hasattr(veille, "SEND_IF_DEGRADED")


def test_injection_de_la_stack_fonctionne():
    """Le mécanisme même de l'application : remplacer la stack sans toucher au moteur."""
    stack, regex = dict(veille.STACK_PRODUCTS), dict(veille.RE_STACK)
    try:
        veille.STACK_PRODUCTS["Zabbix"] = ["zabbix"]
        veille.RE_STACK = {nom: veille._pattern(mots)
                           for nom, mots in veille.STACK_PRODUCTS.items()}
        assert "Zabbix" in veille.detect_stack("Zabbix 7.0.4 fixes a critical RCE")
    finally:
        veille.STACK_PRODUCTS.clear()
        veille.STACK_PRODUCTS.update(stack)
        veille.RE_STACK.clear()
        veille.RE_STACK.update(regex)


def test_perimetre_editable_disponible():
    """L'application n'injecte plus la stack à la main : elle écrit config.json.

    Ce chemin remplace le monkey-patch de STACK_PRODUCTS / RE_STACK, qui dépendait de noms
    internes. S'il disparaît, la configuration de l'utilisateur ne s'applique plus du tout.
    """
    for nom in ("charger_configuration", "valider_configuration", "ConfigurationError"):
        assert hasattr(veille, nom), f"le moteur n'expose plus {nom}"
    assert isinstance(veille.CONFIG_FILE, str) and veille.CONFIG_FILE


def test_fuseau_resolu_et_jamais_utc():
    """Sur Windows sans tzdata, le moteur retombe silencieusement sur UTC."""
    assert ZoneInfo("Europe/Brussels").key == "Europe/Brussels"
    assert str(veille.TZ) != "UTC", "le moteur est retombé sur UTC : tzdata manque"
