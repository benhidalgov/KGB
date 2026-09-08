# Compilador PowerShell de Aplicacion de Escritorio (.exe)
$ErrorActionPreference = "Stop"

Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host "  Compilador de Aplicacion de Escritorio (.exe)" -ForegroundColor Cyan
Write-Host "  Consola de Infraestructura y Operaciones" -ForegroundColor Cyan
Write-Host "=========================================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$PyExe = "python"
if (Test-Path "$ScriptDir\..\env\Scripts\python.exe") {
    $PyExe = "$ScriptDir\..\env\Scripts\python.exe"
} elseif (Test-Path "$ScriptDir\.venv\Scripts\python.exe") {
    $PyExe = "$ScriptDir\.venv\Scripts\python.exe"
}

Write-Host "[*] Interprete de Python: $PyExe" -ForegroundColor Yellow
Write-Host "[*] Ejecutando compilacion con PyInstaller..." -ForegroundColor Yellow

& $PyExe -m PyInstaller desktop_app.spec --noconfirm --clean

Write-Host "[*] Estructurando carpetas de datos en dist\ConsolaOperaciones..." -ForegroundColor Yellow

$DistData = "$ScriptDir\dist\ConsolaOperaciones\data"
$Directories = @(
    "$DistData\docs",
    "$DistData\docs\assets",
    "$DistData\history",
    "$DistData\inbox",
    "$DistData\originals",
    "$ScriptDir\dist\ConsolaOperaciones\.streamlit"
)

foreach ($dir in $Directories) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

if (Test-Path "$ScriptDir\data\mantenimientos.csv") {
    Copy-Item "$ScriptDir\data\mantenimientos.csv" -Destination "$DistData\" -Force
}
if (Test-Path "$ScriptDir\data\categorias.json") {
    Copy-Item "$ScriptDir\data\categorias.json" -Destination "$DistData\" -Force
}
if (Test-Path "$ScriptDir\data\users.json") {
    Copy-Item "$ScriptDir\data\users.json" -Destination "$DistData\" -Force
}
if (Test-Path "$ScriptDir\.streamlit\config.toml") {
    Copy-Item "$ScriptDir\.streamlit\config.toml" -Destination "$ScriptDir\dist\ConsolaOperaciones\.streamlit\" -Force
}

Write-Host ""
Write-Host "=========================================================================" -ForegroundColor Green
Write-Host "  [OK] Compilacion completada con exito!" -ForegroundColor Green
Write-Host "  Ejecutable disponible en:" -ForegroundColor Green
Write-Host "  $ScriptDir\dist\ConsolaOperaciones\ConsolaOperaciones.exe" -ForegroundColor White
Write-Host "=========================================================================" -ForegroundColor Green
