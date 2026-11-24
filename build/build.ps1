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

# La version est ecrite a trois endroits — paquet, proprietes Windows, fenetre A propos.
# Trois copies d'une meme verite derivent toujours : on refuse de construire si elles ne
# disent pas la meme chose.
$versionPaquet = (Select-String -Path "src\secdailybrief\__init__.py" -Pattern '__version__ = "([^"]+)"').Matches[0].Groups[1].Value
$versionPyproject = (Select-String -Path "pyproject.toml" -Pattern '^version = "([^"]+)"').Matches[0].Groups[1].Value
$versionExe = (Select-String -Path "build\version.txt" -Pattern "StringStruct\('FileVersion', '([^']+)'").Matches[0].Groups[1].Value
if ($versionPaquet -ne $versionPyproject -or "$versionPaquet.0" -ne $versionExe) {
    throw "Versions incoherentes : paquet=$versionPaquet pyproject=$versionPyproject exe=$versionExe"
}

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
Copy-Item "CHANGELOG.md" $sortie -Force

$archive = Join-Path $sortieBase "dist\SecDailyBrief-$versionPaquet-win64.zip"
if (Test-Path $archive) {
    try { Remove-Item $archive -Force -ErrorAction Stop }
    catch { throw "Archive verrouillee, fermez-la avant de reconstruire : $archive" }
}
Compress-Archive -Path "$sortie\*" -DestinationPath $archive -ErrorAction Stop
if (-not (Test-Path $archive)) { throw "L'archive n'a pas ete creee." }

# Seconde archive, portable : le meme binaire, accompagne du marqueur qui fait vivre les
# donnees a cote de lui au lieu de %APPDATA%. Deux dossiers distincts, pour qu'aucun des
# deux modes ne puisse heriter du marqueur de l'autre.
$portable = Join-Path $sortieBase "dist\SecDailyBrief-portable"
if (Test-Path $portable) { Remove-Item $portable -Recurse -Force }
Copy-Item $sortie $portable -Recurse -Force
New-Item -ItemType File -Path (Join-Path $portable "portable.flag") -Force | Out-Null
$archivePortable = Join-Path $sortieBase "dist\SecDailyBrief-$versionPaquet-win64-portable.zip"
if (Test-Path $archivePortable) {
    try { Remove-Item $archivePortable -Force -ErrorAction Stop }
    catch { throw "Archive portable verrouillee : $archivePortable" }
}
Compress-Archive -Path "$portable\*" -DestinationPath $archivePortable -ErrorAction Stop

Write-Host "Version : $versionPaquet"
Write-Host "Archive : $archive"
Write-Host "Archive : $archivePortable"
Write-Host "Construit : $exe"
