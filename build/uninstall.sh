#!/usr/bin/env bash
# Retire SecDailyBrief de cette machine : la tâche planifiée, ses unités systemd, ses données.
# Le dossier de l'application n'est pas effacé : l'utilisateur décide de ce qu'il supprime.
set -u

NOM="SecDailyBrief"
DOSSIER_DONNEES="${XDG_DATA_HOME:-$HOME/.local/share}/SecDailyBrief"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}/SecDailyBrief"

echo "== Tâche planifiée =="
if command -v systemctl >/dev/null 2>&1; then
    for unite in "$NOM" "$NOM-Alerte"; do
        systemctl --user disable --now "$unite.timer" 2>/dev/null && echo "  $unite.timer désactivé"
        rm -f "$HOME/.config/systemd/user/$unite.timer" "$HOME/.config/systemd/user/$unite.service"
    done
    systemctl --user daemon-reload 2>/dev/null || true
else
    echo "  systemctl absent : rien à retirer"
fi

echo "== Données =="
for dossier in "$CONFIG" "$DOSSIER_DONNEES"; do
    if [ -d "$dossier" ]; then
        echo "  $dossier"
        echo "    (contient votre configuration et vos secrets chiffrés)"
    fi
done

echo
echo "Pour tout effacer, y compris ces deux dossiers :"
echo "  rm -rf \"$CONFIG\" \"$DOSSIER_DONNEES\""
echo
echo "Le dossier de l'application peut ensuite être supprimé à la main."
