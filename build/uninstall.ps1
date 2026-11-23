# Desinstalle SecDailyBrief : retire la tache planifiee, et propose de supprimer les donnees.
#
# Texte volontairement sans accents : Windows PowerShell 5.1 lit un script sans BOM comme
# de l'ANSI, et les accents y deviennent des caracteres invalides.

$ErrorActionPreference = "Continue"
$tache = "SecDailyBrief"

Write-Host "== SecDailyBrief : desinstallation =="

schtasks /Query /TN $tache *> $null
if ($LASTEXITCODE -eq 0) {
    schtasks /Delete /TN $tache /F | Out-Null
    Write-Host "Tache planifiee supprimee."
} else {
    Write-Host "Aucune tache planifiee a retirer."
}

$donnees = Join-Path $env:APPDATA "SecDailyBrief"
if (Test-Path $donnees) {
    Write-Host ""
    Write-Host "Les donnees se trouvent dans : $donnees"
    Write-Host "(configuration, mot de passe chiffre, etat, journal)"
    $reponse = Read-Host "Supprimer aussi ces donnees ? [o/N]"
    if ($reponse -match '^[oOyY]') {
        Remove-Item $donnees -Recurse -Force
        Write-Host "Donnees supprimees."
    } else {
        Write-Host "Donnees conservees."
    }
}

Write-Host ""
Write-Host "Termine. Vous pouvez maintenant effacer le dossier SecDailyBrief."
Write-Host "Cette fenetre se ferme dans 10 secondes."
Start-Sleep -Seconds 10
