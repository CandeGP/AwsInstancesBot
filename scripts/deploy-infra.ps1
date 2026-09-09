[CmdletBinding()]
param(
    [switch]$Apply
)

$ErrorActionPreference = "Stop"
$infraPath = Join-Path $PSScriptRoot "..\infra"

Push-Location $infraPath
try {
    terraform init
    terraform fmt -check
    terraform validate

    $planPath = Join-Path $infraPath "tfplan"
    terraform plan -out=$planPath

    if ($Apply) {
        terraform apply $planPath
    } else {
        Write-Host "Plan listo. Para aplicar los cambios ejecuta: .\scripts\deploy-infra.ps1 -Apply"
    }
}
finally {
    Pop-Location
}
