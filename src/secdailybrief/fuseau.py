"""Quelle heure est-il, chez l'utilisateur ?

Le fuseau par défaut est Bruxelles, celui de l'auteur. Imposer Bruxelles à un utilisateur de
Québec ou de Lisbonne n'est pas faux — le programme enverrait simplement son rapport à une
heure qui n'est pas la sienne.

Windows nomme ses fuseaux autrement qu'IANA (« Romance Standard Time »), et sa table est plus
grosse que ce qu'un programme de cette taille peut recopier. Deux règles :

- la table ci-dessous couvre les zones les plus fréquentes, avec leur représentant IANA ;
- hors de cette table, on garde le défaut, et on ne remplace jamais un choix explicite.

Les fuseaux regroupés par Windows (Bruxelles, Paris et Madrid partagent « Romance Standard
Time ») sont fonctionnellement équivalents : même décalage, mêmes changements d'heure.
"""
from __future__ import annotations

import sys

FUSEAU_PAR_DEFAUT = "Europe/Brussels"

# Nom Windows -> zone IANA représentative. Table volontairement courte : mieux vaut un
# défaut assumé qu'une correspondance inventée.
CORRESPONDANCES = {
    "Romance Standard Time": "Europe/Paris",
    "W. Europe Standard Time": "Europe/Berlin",
    "Central Europe Standard Time": "Europe/Budapest",
    "Central European Standard Time": "Europe/Warsaw",
    "GTB Standard Time": "Europe/Bucharest",
    "E. Europe Standard Time": "Europe/Chisinau",
    "FLE Standard Time": "Europe/Kyiv",
    "Russian Standard Time": "Europe/Moscow",
    "GMT Standard Time": "Europe/London",
    "Greenwich Standard Time": "Atlantic/Reykjavik",
    "Morocco Standard Time": "Africa/Casablanca",
    "Egypt Standard Time": "Africa/Cairo",
    "South Africa Standard Time": "Africa/Johannesburg",
    "W. Central Africa Standard Time": "Africa/Lagos",
    "Turkey Standard Time": "Europe/Istanbul",
    "Israel Standard Time": "Asia/Jerusalem",
    "Arabian Standard Time": "Asia/Dubai",
    "Iran Standard Time": "Asia/Tehran",
    "India Standard Time": "Asia/Kolkata",
    "China Standard Time": "Asia/Shanghai",
    "Tokyo Standard Time": "Asia/Tokyo",
    "Korea Standard Time": "Asia/Seoul",
    "Singapore Standard Time": "Asia/Singapore",
    "AUS Eastern Standard Time": "Australia/Sydney",
    "New Zealand Standard Time": "Pacific/Auckland",
    "Eastern Standard Time": "America/New_York",
    "Central Standard Time": "America/Chicago",
    "Mountain Standard Time": "America/Denver",
    "Pacific Standard Time": "America/Los_Angeles",
    "Atlantic Standard Time": "America/Halifax",
    "Newfoundland Standard Time": "America/St_Johns",
    "SA Pacific Standard Time": "America/Bogota",
    "E. South America Standard Time": "America/Sao_Paulo",
    "Argentina Standard Time": "America/Argentina/Buenos_Aires",
    "Pacific SA Standard Time": "America/Santiago",
    "UTC": "UTC",
}


def nom_windows() -> str | None:
    """Nom du fuseau tel que Windows le connaît, ou None hors de Windows."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                            r"SYSTEM\CurrentControlSet\Control\TimeZoneInformation") as cle:
            valeur, _ = winreg.QueryValueEx(cle, "TimeZoneKeyName")
    except (OSError, ImportError):
        return None
    return valeur if isinstance(valeur, str) and valeur else None


def _existe(zone: str) -> bool:
    """La zone est-elle connue de la base IANA embarquée ?"""
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(zone)
    except Exception:                       # noqa: BLE001 - zone inconnue ou base absente
        return False
    return True


def zone_iana(defaut: str = FUSEAU_PAR_DEFAUT) -> str:
    """Zone IANA de cette machine, ou le défaut si elle n'est pas dans la table."""
    zone = CORRESPONDANCES.get(nom_windows() or "")
    if zone and _existe(zone):
        return zone
    return defaut
