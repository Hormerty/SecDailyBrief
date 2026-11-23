"""Lance l'application, capture sa fenêtre, la referme.

La capture passe par PrintWindow : photographier l'écran ramènerait la fenêtre qui se
trouve devant, pas la nôtre — ce qui est arrivé à la première tentative.
"""
from __future__ import annotations

import ctypes
import os
import subprocess
import tempfile
import time
from ctypes import wintypes
from pathlib import Path

from PIL import Image

RACINE = Path(__file__).resolve().parent.parent
dossier = Path(tempfile.mkdtemp(prefix="secdailybrief-shot-"))
env = dict(os.environ, SECDailyBrief_DATA=str(dossier),
           PYTHONPATH=str(RACINE / "src"))

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


class BITMAPINFO(ctypes.Structure):
    _fields_ = [("bmiHeader", BITMAPINFOHEADER), ("bmiColors", wintypes.DWORD * 3)]


def capturer_fenetre(hwnd: int) -> Image.Image:
    rect = RECT()
    # GetWindowRect, pas GetClientRect : PrintWindow dessine la fenêtre entière, barre de
    # titre comprise. Un bitmap à la taille du client rogne le bas — et le pied de fenêtre
    # est exactement là.
    user32.GetWindowRect(ctypes.c_void_p(hwnd), ctypes.byref(rect))
    largeur, hauteur = rect.right - rect.left, rect.bottom - rect.top

    dc_fenetre = user32.GetWindowDC(ctypes.c_void_p(hwnd))
    dc_memoire = gdi32.CreateCompatibleDC(dc_fenetre)
    bitmap = gdi32.CreateCompatibleBitmap(dc_fenetre, largeur, hauteur)
    gdi32.SelectObject(dc_memoire, bitmap)

    # 2 = PW_RENDERFULLCONTENT, nécessaire pour les fenêtres composées (thème ttk).
    if not user32.PrintWindow(ctypes.c_void_p(hwnd), dc_memoire, 2):
        user32.PrintWindow(ctypes.c_void_p(hwnd), dc_memoire, 0)

    info = BITMAPINFO()
    info.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    info.bmiHeader.biWidth = largeur
    info.bmiHeader.biHeight = -hauteur          # top-down
    info.bmiHeader.biPlanes = 1
    info.bmiHeader.biBitCount = 32
    info.bmiHeader.biCompression = 0            # BI_RGB

    tampon = ctypes.create_string_buffer(largeur * hauteur * 4)
    gdi32.GetDIBits(dc_memoire, bitmap, 0, hauteur, tampon, ctypes.byref(info), 0)

    image = Image.frombuffer("RGBA", (largeur, hauteur), tampon, "raw", "BGRA", 0, 1)
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(dc_memoire)
    user32.ReleaseDC(ctypes.c_void_p(hwnd), dc_fenetre)
    return image.convert("RGB")

def main() -> int:
    python_application = RACINE / ".venv" / "Scripts" / "python.exe"
    processus = subprocess.Popen([str(python_application), "-m", "secdailybrief"],
                                 cwd=str(RACINE), env=env)
    try:
        hwnd = None
        for _ in range(40):
            hwnd = user32.FindWindowW(None, "SecDailyBrief")
            if hwnd:
                break
            time.sleep(0.25)
        if not hwnd:
            print("fenetre introuvable")
            return 1

        time.sleep(0.8)  # laisser ttk appliquer son thème
        image = capturer_fenetre(hwnd)
        sortie = Path(tempfile.gettempdir()) / "secdailybrief-wizard.png"
        image.save(sortie)
        print("capture :", sortie, image.size)
        return 0
    finally:
        processus.terminate()
        try:
            processus.wait(timeout=5)
        except subprocess.TimeoutExpired:
            processus.kill()


if __name__ == "__main__":
    raise SystemExit(main())
