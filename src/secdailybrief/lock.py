"""Verrou mono-instance : deux exécutions simultanées se marcheraient dessus.

Le cas réel n'est pas théorique : la tâche planifiée démarre à 06:00 pendant que
l'utilisateur clique « Lancer maintenant » dans le panneau. Sans verrou, deux collectes
partent en parallèle et les deux peuvent envoyer un rapport.

Le verrou est un mutex Windows nommé dans l'espace `Local\\`, donc partagé entre les
sessions d'un même utilisateur mais pas entre utilisateurs — deux comptes Windows sur la
même machine doivent pouvoir faire tourner leur propre copie.
"""
from __future__ import annotations

import contextlib
import ctypes
from ctypes import wintypes

ERROR_ALREADY_EXISTS = 183
NOM_PAR_DEFAUT = "Local\\SecDailyBrief"


@contextlib.contextmanager
def instance_unique(nom: str = NOM_PAR_DEFAUT):
    """Rend True si l'on est la seule instance, False si une autre tourne déjà."""
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
