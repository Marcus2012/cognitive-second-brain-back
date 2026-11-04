$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    $brainPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $brainPython)) {
        throw "Falta .venv. Ejecuta: python -m venv .venv"
    }
    & $brainPython -m uvicorn app.main:app --reload
    if ($LASTEXITCODE -ne 0) {
        throw "No se pudo iniciar el backend. Revisa el error anterior."
    }
} finally {
    Pop-Location
}
