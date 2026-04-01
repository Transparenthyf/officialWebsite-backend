$ErrorActionPreference = "Stop"

$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $here

$py = "python"
$venvPython = Join-Path $here ".venv\Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
  Write-Host "Creating venv: backend/.venv"
  & $py -m venv ".venv"
}

Write-Host "Installing dependencies..."
& $venvPython -m pip install -U pip
& $venvPython -m pip install -r "requirements.txt"

Write-Host "Starting backend..."
& $venvPython "app.py"

