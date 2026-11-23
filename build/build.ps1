# Empaquette SecDailyBrief en dossier (pas en fichier unique : moins de faux positifs
# antivirus, et un démarrage sans décompression).
#
# Usage :  pwsh -File build\build.ps1
# Résultat : dist\SecDailyBrief\SecDailyBrief.exe

$ErrorActionPreference = "Stop"
$racine = Split-Path -Parent $PSScriptRoot
Set-Location $racine

$python = Join-Path $racine ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) {
    throw "Environnement absent : créer .venv et installer requirements.txt + requirements-dev.txt"
}

# Le moteur doit être présent et intact avant d'empaqueter : un binaire qui embarque un
# moteur altéré est indétectable une fois livré.
& $python tools\fetch_engine.py --verify
if ($LASTEXITCODE -ne 0) { throw "Le moteur ne correspond pas au verrou." }

# Le moteur est embarqué comme DONNÉE (--add-data), mais il est AUSSI déclaré comme module
# caché, avec vendor\ dans les chemins d'analyse : PyInstaller lit alors ses imports
# (feedparser, sqlite3, requests…) et embarque tout. Sans cela, l'analyse ne voyait que
# l'application : le premier binaire livré démarrait avec un moteur inimportable —
# « feedparser » manquait, puis « sqlite3 ». Une dépendance à la fois, c'est trois rebuilds.

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name SecDailyBrief `
    --workpath "work" `
    --distpath "dist" `
    --paths "src" `
    --paths "vendor" `
    --hidden-import "veille" `
    --hidden-import "tzdata" `
    --icon "assets\SecDailyBrief.ico" `
    --version-file "build\version.txt" `
    --add-data "vendor;vendor" `
    --add-data "assets;assets" `
    main.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller a échoué." }

# Garde-fou : une archive produite à partir d'un dossier incomplet est indétectable pour
# qui la télécharge. C'est arrivé une fois — l'application tournait depuis dist\, PyInstaller
# a vidé le dossier sans pouvoir le réécrire, et le ZIP s'est fait à partir des restes.
$exe = Join-Path $racine "dist\SecDailyBrief\SecDailyBrief.exe"
if (-not (Test-Path $exe)) {
    throw "PyInstaller n'a pas produit dist\SecDailyBrief\SecDailyBrief.exe (dossier incomplet ou verrouille)."
}
if ((Get-Item $exe).Length -lt 1MB) {
    throw "Executable suspect : $((Get-Item $exe).Length) octets."
}

# Assemblage de l'archive : le binaire, mais aussi ce qui permet de désinstaller et de
# comprendre ce qu'on vient d'installer.
$sortie = Join-Path $racine "dist\SecDailyBrief"
Copy-Item "build\README.txt" $sortie -Force
Copy-Item "build\uninstall.ps1" $sortie -Force
Copy-Item "LICENSE" $sortie -Force

$archive = Join-Path $racine "dist\SecDailyBrief-1.0.0-win64.zip"
if (Test-Path $archive) {
    try { Remove-Item $archive -Force -ErrorAction Stop }
    catch { throw "Archive verrouillee, fermez-la avant de reconstruire : $archive" }
}
Compress-Archive -Path "$sortie\*" -DestinationPath $archive -ErrorAction Stop
if (-not (Test-Path $archive)) { throw "L'archive n'a pas ete creee." }
Write-Host "Archive : dist\SecDailyBrief-1.0.0-win64.zip"
Write-Host "Construit : dist\SecDailyBrief\SecDailyBrief.exe"
