"""Ce qui diffère d'un système à l'autre, derrière une interface unique.

Trois capacités seulement : **chiffrer un secret** localement, **verrouiller l'instance** pour
que deux exécutions ne se superposent pas, et **savoir où écrire** les données. Le reste du
code appelle ces fonctions sans savoir sur quoi il tourne.

Les modules de l'application gardent leur API — `secrets.proteger`, `lock.instance_unique`,
`paths.dossier_donnees` — et délèguent ici. Un port vers une nouvelle plateforme consiste donc
à écrire un fichier de plus, pas à toucher aux appelants.
"""
from __future__ import annotations

import sys

if sys.platform == "win32":
    from . import windows as impl
else:                                   # Linux, et par extension macOS
    from . import linux as impl

nom = impl.NOM
chiffrer = impl.chiffrer
dechiffrer = impl.dechiffrer
verrou_instance = impl.verrou_instance
dossier_donnees = impl.dossier_donnees

__all__ = ["nom", "chiffrer", "dechiffrer", "verrou_instance", "dossier_donnees"]
