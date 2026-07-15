[CmdletBinding()]
param(
    [string] $Python = "python"
)

$ErrorActionPreference = "Stop"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$VenvDirectory = Join-Path $RepoRoot ".venv"

Push-Location $RepoRoot
try {
    if (-not (Test-Path $VenvDirectory)) {
        & $Python -m venv $VenvDirectory
    }

    $VenvPython = Join-Path $VenvDirectory "Scripts/python.exe"
    & $VenvPython -m pip install --upgrade pip
    & $VenvPython -m pip install -r requirements.txt
    & $VenvPython scripts/build_site.py

    Write-Host ""
    Write-Host "Build complete: $RepoRoot/dist/index.html"
}
finally {
    Pop-Location
}
