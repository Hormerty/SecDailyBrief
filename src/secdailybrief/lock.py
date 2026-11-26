"""Verrou mono-instance : deux exécutions simultanées se marcheraient dessus.

Le cas réel n'est pas théorique : la tâche planifiée démarre à 06:00 pendant que
l'utilisateur clique « Lancer maintenant » dans le panneau. Sans verrou, deux collectes
partent en parallèle et les deux peuvent envoyer un rapport.

Le mécanisme dépend du système — mutex nommé sous Windows, `flock` sous Linux — et c'est
`plateforme` qui tranche. Le contrat, lui, ne change pas : rendre True si l'on est seule,
False si une autre instance tourne déjà.
"""
from __future__ import annotations

from . import plateforme

NOM_PAR_DEFAUT = "Local\\SecDailyBrief"

instance_unique = plateforme.verrou_instance

__all__ = ["instance_unique", "NOM_PAR_DEFAUT"]
