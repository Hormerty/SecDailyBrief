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

"$python" -m PyInstaller \
    --noconfirm \
    --clean \
    --windowed \
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
