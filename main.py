"""Point d'entrée de l'exécutable : PyInstaller n'embarque pas `python -m`.

Tout le travail est dans le paquet ; ce fichier ne fait que l'appeler, pour que le même
code serve en développement (`python -m secdailybrief`) et dans le binaire.

L'import de `app` en tête est volontaire : c'est ce qui rend `tkinter` visible à l'analyse
statique de PyInstaller. Importé paresseusement, il n'était pas embarqué, et l'exécutable
démarrait sans interface — un binaire qui ne fait rien, sans message.
"""
from secdailybrief import app as _app  # noqa: F401
from secdailybrief.__main__ import main

if __name__ == "__main__":
    raise SystemExit(main())
