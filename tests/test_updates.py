"""Tests de la comparaison de versions : le bandeau ne doit mentir ni s'afficher à tort."""
from __future__ import annotations

import json
import urllib.error

from secdailybrief import updates


def test_numeros_normalise():
    assert updates.numeros("1.2.3") == (1, 2, 3)
    assert updates.numeros("v1.2.0") == (1, 2, 0)
    assert updates.numeros("2.0") == (2, 0, 0)
    assert updates.numeros("1.0.1-beta") == (1, 0, 1)


def test_comparaison():
    assert updates.plus_recente("1.0.0", "v1.0.1") is True
    assert updates.plus_recente("1.0.0", "1.1.0") is True
    assert updates.plus_recente("1.0.0", "1.0.0") is False
    assert updates.plus_recente("1.2.0", "1.1.9") is False
    assert updates.plus_recente("1.0.0", None) is False


def test_api_injoignable_rend_none(monkeypatch):
    def echoue(*arguments, **options):
        raise urllib.error.URLError("hors ligne")

    monkeypatch.setattr(updates.urllib.request, "urlopen", echoue)
    assert updates.derniere_publiee() is None


class _FausseReponse:
    def __init__(self, charge: bytes) -> None:
        self._charge = charge

    def read(self) -> bytes:
        return self._charge

    def __enter__(self):
        return self

    def __exit__(self, *arguments):
        return False


def test_derniere_publiee_lit_le_tag(monkeypatch):
    charge = json.dumps({"tag_name": "v1.1.0"}).encode("utf-8")
    monkeypatch.setattr(updates.urllib.request, "urlopen",
                        lambda *a, **k: _FausseReponse(charge))
    assert updates.derniere_publiee() == "v1.1.0"


def test_reponse_sans_tag_rend_none(monkeypatch):
    charge = json.dumps({"message": "Not Found"}).encode("utf-8")
    monkeypatch.setattr(updates.urllib.request, "urlopen",
                        lambda *a, **k: _FausseReponse(charge))
    assert updates.derniere_publiee() is None
