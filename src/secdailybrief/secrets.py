"""Chiffrement local du mot de passe d'application, par DPAPI.

DPAPI lie le chiffré au compte Windows qui l'a produit : un autre utilisateur de la même
machine, ou le même disque monté ailleurs, ne peut pas le déchiffrer. C'est exactement ce
qu'il faut pour un mot de passe SMTP qui doit survivre à un redémarrage sans jamais
exister en clair dans un fichier.

Ce que ça ne protège pas : un programme qui tournerait déjà sous le compte de
l'utilisateur. Aucun stockage local ne protège de ça, et il vaut mieux l'écrire ici que de
laisser croire à une sécurité qu'on n'a pas.
"""
from __future__ import annotations

import base64
import ctypes
import json
from ctypes import wintypes
from pathlib import Path

CRYPTPROTECT_UI_FORBIDDEN = 0x01
DESCRIPTION = "SecDailyBrief"


class _Blob(ctypes.Structure):
    _fields_ = [("cbData", wintypes.DWORD), ("pbData", ctypes.POINTER(ctypes.c_char))]


def _bibliotheques():
    if not hasattr(ctypes, "windll"):  # pragma: no cover - Windows uniquement
        raise OSError("DPAPI n'existe que sous Windows")
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    crypt32.CryptProtectData.argtypes = [
        ctypes.POINTER(_Blob), wintypes.LPCWSTR, ctypes.POINTER(_Blob),
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    crypt32.CryptProtectData.restype = wintypes.BOOL
    crypt32.CryptUnprotectData.argtypes = [
        ctypes.POINTER(_Blob), ctypes.POINTER(wintypes.LPWSTR), ctypes.POINTER(_Blob),
        ctypes.c_void_p, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(_Blob)]
    crypt32.CryptUnprotectData.restype = wintypes.BOOL
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    return crypt32, kernel32


def _entree(donnees: bytes):
    tampon = ctypes.create_string_buffer(donnees, len(donnees))
    return _Blob(len(donnees), ctypes.cast(tampon, ctypes.POINTER(ctypes.c_char))), tampon


def proteger(texte: str) -> bytes:
    crypt32, kernel32 = _bibliotheques()
    entree, _tampon = _entree(texte.encode("utf-8"))
    sortie = _Blob()
    ok = crypt32.CryptProtectData(ctypes.byref(entree), DESCRIPTION, None, None, None,
                                  CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(sortie))
    if not ok:
        raise OSError(ctypes.GetLastError(), "CryptProtectData a echoue")
    try:
        return ctypes.string_at(sortie.pbData, sortie.cbData)
    finally:
        kernel32.LocalFree(sortie.pbData)


def deproteger(chiffre: bytes) -> str:
    crypt32, kernel32 = _bibliotheques()
    entree, _tampon = _entree(chiffre)
    sortie = _Blob()
    ok = crypt32.CryptUnprotectData(ctypes.byref(entree), None, None, None, None,
                                    CRYPTPROTECT_UI_FORBIDDEN, ctypes.byref(sortie))
    if not ok:
        raise OSError(ctypes.GetLastError(),
                      "CryptUnprotectData a echoue : ce secret n'appartient pas a ce compte Windows")
    try:
        return ctypes.string_at(sortie.pbData, sortie.cbData).decode("utf-8")
    finally:
        kernel32.LocalFree(sortie.pbData)


def enregistrer(chemin: Path, mot_de_passe: str) -> None:
    """Écrit le secret chiffré, en base64 pour rester inspectable sans être lisible."""
    chemin.parent.mkdir(parents=True, exist_ok=True)
    chemin.write_bytes(base64.b64encode(proteger(mot_de_passe)))


def charger(chemin: Path) -> str | None:
    """Relit le secret, ou None s'il n'y en a pas encore."""
    if not chemin.exists():
        return None
    return deproteger(base64.b64decode(chemin.read_bytes()))


def effacer(chemin: Path) -> None:
    chemin.unlink(missing_ok=True)


def enregistrer_jetons(chemin: Path, jetons: dict[str, str]) -> None:
    """Chiffre tous les secrets ensemble : un mot de passe SMTP, des clés d'API, un jeton.

    Un seul blob DPAPI, donc un seul fichier à sauvegarder, à déplacer ou à effacer — et
    aucune clé en clair dans le JSON de configuration, qui reste lisible.
    """
    enregistrer(chemin, json.dumps(jetons, ensure_ascii=False))


def charger_jetons(chemin: Path) -> dict[str, str]:
    """Relit le dictionnaire de secrets ; {} s'il n'y en a pas encore."""
    texte = charger(chemin)
    if not texte:
        return {}
    try:
        donnees = json.loads(texte)
    except json.JSONDecodeError:
        return {}
    return {cle: valeur for cle, valeur in donnees.items() if isinstance(valeur, str)}
