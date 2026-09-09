[CmdletBinding()]
param(
    [switch]$ConfirmDestroy
)

$ErrorActionPreference = "Stop"
$infraPath = Join-Path $PSScriptRoot "..\infra"

if (-not $ConfirmDestroy) {
    Write-Host "No se eliminaron recursos. Ejecuta .\scripts\destroy-infra.ps1 -ConfirmDestroy para confirmar."
    exit 0
}

Push-Location $infraPath
try {
    terraform destroy
}
finally {
    Pop-Location
}
