# Empaquette SecDailyBrief en dossier (pas en fichier unique : moins de faux positifs
# antivirus, et un démarrage sans décompression).
#
# Usage :  powershell -NoProfile -ExecutionPolicy Bypass -File build\build.ps1
# Sortie  : $env:SDB_SORTIE si défini, sinon D:\SecDailyBrief-build
#
# Ce dossier de sortie par défaut n'est pas un caprice : dans l'arborescence du dépôt,
# l'antivirus renomme ou retire le binaire dès qu'il est produit — les fichiers qu'il
# laisse n'ont même plus leurs propriétés de version. Hors de cette arborescence, le même
# binaire survit intact.

$ErrorActionPreference = "Stop"
$racine = Split-Path -Parent $PSScriptRoot
Set-Location $racine

$sortieBase = if ($env:SDB_SORTIE) { $env:SDB_SORTIE } else { "D:\SecDailyBrief-build" }

$python = Join-Path $racine ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Environnement absent : creer .venv et installer requirements.txt + requirements-dev.txt"
}

# Le moteur doit etre present et intact avant d'empaqueter : un binaire qui embarque un
# moteur altere est indetectable une fois livre.
& $python tools\fetch_engine.py --verify
if ($LASTEXITCODE -ne 0) { throw "Le moteur ne correspond pas au verrou." }

# Le moteur est embarque comme DONNEE (--add-data), mais il est AUSSI declare comme module
# cache, avec vendor\ dans les chemins d'analyse : PyInstaller lit alors ses imports
# (feedparser, sqlite3, requests...) et embarque tout. Sans cela, l'analyse ne voyait que
# l'application, et le premier binaire livre demarrait avec un moteur inimportable.

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name SecDailyBrief `
    --workpath "$sortieBase\work" `
    --distpath "$sortieBase\dist" `
    --paths "src" `
    --paths "vendor" `
    --hidden-import "veille" `
    --hidden-import "tzdata" `
    --collect-data "certifi" `
    --icon "assets\SecDailyBrief.ico" `
    --version-file "build\version.txt" `
    --add-data "vendor;vendor" `
    --add-data "assets;assets" `
    main.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller a echoue." }

# Garde-fou : une archive produite a partir d'un dossier incomplet est indetectable pour
# qui la telecharge. C'est arrive une fois — l'application tournait depuis le dossier de
# sortie, PyInstaller l'a vide sans pouvoir le reecrire, et le ZIP s'est fait des restes.
$exe = Join-Path $sortieBase "dist\SecDailyBrief\SecDailyBrief.exe"
if (-not (Test-Path $exe)) {
    throw "PyInstaller n'a pas produit $exe (dossier incomplet ou verrouille)."
}
if ((Get-Item $exe).Length -lt 1MB) {
    throw "Executable suspect : $((Get-Item $exe).Length) octets."
}

# Assemblage de l'archive : le binaire, mais aussi ce qui permet de desinstaller et de
# comprendre ce qu'on vient d'installer.
$sortie = Join-Path $sortieBase "dist\SecDailyBrief"
Copy-Item "build\README.txt" $sortie -Force
Copy-Item "build\uninstall.ps1" $sortie -Force
Copy-Item "LICENSE" $sortie -Force

$archive = Join-Path $sortieBase "dist\SecDailyBrief-1.0.0-win64.zip"
if (Test-Path $archive) {
    try { Remove-Item $archive -Force -ErrorAction Stop }
    catch { throw "Archive verrouillee, fermez-la avant de reconstruire : $archive" }
}
Compress-Archive -Path "$sortie\*" -DestinationPath $archive -ErrorAction Stop
if (-not (Test-Path $archive)) { throw "L'archive n'a pas ete creee." }

Write-Host "Archive : $archive"
Write-Host "Construit : $exe"
