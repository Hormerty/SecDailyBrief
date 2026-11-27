#!/usr/bin/env bash
# Construction Linux : mêmes étapes que build.ps1, mêmes garde-fous.
#
# PyInstaller ne compile pas en croisé : ce script doit tourner sous Linux. En échange, il
# refuse de produire une archive incomplète — c'est la leçon de la 1.4.3, publiée avec un
# dossier certifi vide.
set -euo pipefail

cd "$(dirname "$0")/.."
python="${PYTHON:-python3}"

version="$("$python" -c 'import sys; sys.path.insert(0, "src"); import secdailybrief; print(secdailybrief.__version__)')"
echo "Version : $version"

# Le moteur doit correspondre au verrou avant tout emballage.
"$python" tools/fetch_engine.py --verify

# Le paquet de certificats est ajouté explicitement : --collect-data l'a déjà oublié une fois.
cacert="$("$python" -c 'import certifi; print(certifi.where())')"
if [ ! -f "$cacert" ]; then
    echo "cacert.pem introuvable dans l'environnement : $cacert" >&2
    exit 1
fi

sortie="build/dist"
rm -rf "$sortie"

# La bibliothèque Python d'Ubuntu n'est pas strippée : 28 Mo de tables de symboles dans
# l'archive, contre 6 Mo une fois `strip` passé. --strip le fait pour toutes les bibliothèques,
# ce qui ramenait l'archive Linux de 31 à 10 Mo.

# La version de glibc exigée par le binaire suit celle du système qui le construit. Construit
# sur Ubuntu 26.04 (glibc 2.42), il refusait de démarrer sur Debian 13 (2.41) — rapporté le
# 26 novembre 2026. La construction se fait donc sur une base plus ancienne, et ce contrôle
# empêche qu'un runner mis à jour nous ramène le défaut en silence.
GLIBC_MAX_ACCEPTEE="${SDB_GLIBC_MAX:-}"

echo "== construction =="
"$python" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
    --strip \
    --name SecDailyBrief \
    --workpath "build/work" \
    --distpath "$sortie" \
    --paths src \
    --paths vendor \
    --hidden-import veille \
    --hidden-import tzdata \
    --collect-data certifi \
    --add-data "vendor:vendor" \
    --add-data "assets:assets" \
    --add-data "$cacert:certifi" \
    main.py

exe="$sortie/SecDailyBrief/SecDailyBrief"
if [ ! -x "$exe" ]; then
    echo "PyInstaller n'a pas produit $exe" >&2
    exit 1
fi
if [ ! -f "$sortie/SecDailyBrief/_internal/certifi/cacert.pem" ]; then
    echo "cacert.pem absent du binaire : $sortie/SecDailyBrief/_internal/certifi/cacert.pem" >&2
    exit 1
fi

# La version annoncée dans le README livré doit être celle du paquet.
sed -i "s/^SecDailyBrief .*/SecDailyBrief $version/" build/README.txt

cp build/README.txt build/uninstall.sh "$sortie/SecDailyBrief/" 2>/dev/null || true

archive="$sortie/SecDailyBrief-$version-linux-x86_64.tar.gz"
tar -C "$sortie" -czf "$archive" SecDailyBrief

# Variante portable : données à côté du binaire plutôt que dans XDG.
portable="$sortie/SecDailyBrief-portable"
rm -rf "$portable"
cp -a "$sortie/SecDailyBrief" "$portable"
touch "$portable/portable.flag"
archivePortable="$sortie/SecDailyBrief-$version-linux-x86_64-portable.tar.gz"
tar -C "$sortie" -czf "$archivePortable" SecDailyBrief-portable

echo "Archive : $archive"
echo "Archive : $archivePortable"
echo "Construit : $exe"

# Contrôle de compatibilité : quelle version de glibc le binaire réclame-t-il ?
glibc_exigee="$(objdump -T "$sortie/SecDailyBrief/_internal/"*.so* "$exe" 2>/dev/null \
  | grep -o 'GLIBC_[0-9.]*' | sort -V -u | tail -1)"
echo "glibc exigee : ${glibc_exigee:-inconnue}"
if [ -n "$GLIBC_MAX_ACCEPTEE" ] && [ -n "$glibc_exigee" ]; then
  if [ "$(printf '%s\n%s\n' "$GLIBC_MAX_ACCEPTEE" "${glibc_exigee#GLIBC_}" | sort -V | tail -1)" != "$GLIBC_MAX_ACCEPTEE" ]; then
    echo "ECHEC : le binaire exige $glibc_exigee, au-dela de $GLIBC_MAX_ACCEPTEE" >&2
    echo "        Construisez sur une base plus ancienne (ubuntu-22.04)." >&2
    exit 1
  fi
  echo "compatibilite : conforme (maximum autorise $GLIBC_MAX_ACCEPTEE)"
fi
