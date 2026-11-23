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

& $python -m PyInstaller `
    --noconfirm `
    --clean `
    --windowed `
    --name SecDailyBrief `
    --workpath "work" `
    --distpath "dist" `
    --paths "src" `
    --icon "assets\SecDailyBrief.ico" `
    --version-file "build\version.txt" `
    --add-data "vendor;vendor" `
    --add-data "assets;assets" `
    main.py

if ($LASTEXITCODE -ne 0) { throw "PyInstaller a échoué." }

# Assemblage de l'archive : le binaire, mais aussi ce qui permet de désinstaller et de
# comprendre ce qu'on vient d'installer.
$sortie = Join-Path $racine "dist\SecDailyBrief"
Copy-Item "build\README.txt" $sortie -Force
Copy-Item "build\uninstall.ps1" $sortie -Force
Copy-Item "LICENSE" $sortie -Force

$archive = Join-Path $racine "dist\SecDailyBrief-1.0.0-win64.zip"
if (Test-Path $archive) { Remove-Item $archive -Force }
Compress-Archive -Path "$sortie\*" -DestinationPath $archive
Write-Host "Archive : dist\SecDailyBrief-1.0.0-win64.zip"
Write-Host "Construit : dist\SecDailyBrief\SecDailyBrief.exe"
