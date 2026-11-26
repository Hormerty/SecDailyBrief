"""Implémentation Windows : DPAPI, mutex nommé, profil utilisateur.

DPAPI lie le chiffré au compte Windows qui l'a produit : un autre utilisateur de la même
machine, ou le même disque monté ailleurs, ne peut pas le déchiffrer. C'est exactement ce
qu'il faut pour un mot de passe SMTP qui doit survivre à un redémarrage sans jamais exister
en clair dans un fichier.

Ce que ça ne protège pas : un programme qui tournerait déjà sous le compte de l'utilisateur.
Aucun stockage local ne protège de ça, et il vaut mieux l'écrire ici que de laisser croire à
une sécurité qu'on n'a pas.
"""
from __future__ import annotations

import contextlib
import ctypes
from ctypes import wintypes
from pathlib import Path

NOM = "DPAPI (Windows)"

CRYPTPROTECT_UI_FORBIDDEN = 0x01
DESCRIPTION = "SecDailyBrief"
ERROR_ALREADY_EXISTS = 183
NOM_PAR_DEFAUT = "Local\\SecDailyBrief"


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


def chiffrer(texte: str) -> bytes:
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


def dechiffrer(chiffre: bytes) -> str:
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


@contextlib.contextmanager
def verrou_instance(nom: str = NOM_PAR_DEFAUT):
    """Mutex nommé dans l'espace `Local\\` : partagé entre sessions d'un même utilisateur.

    Deux comptes Windows sur la même machine doivent pouvoir faire tourner leur propre copie.
    """
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR]
    kernel32.CreateMutexW.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL

    handle = kernel32.CreateMutexW(None, True, nom)
    if not handle:
        raise OSError(ctypes.get_last_error(), "CreateMutexW a echoue")
    deja_pris = ctypes.get_last_error() == ERROR_ALREADY_EXISTS
    try:
        yield not deja_pris
    finally:
        kernel32.CloseHandle(handle)


def dossier_donnees() -> Path | None:
    """Windows garde sa logique historique : profil utilisateur, ou portable."""
    return None
