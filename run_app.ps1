Write-Host "Iniciando KGB - Camarada de Infraestructura y Operaciones..." -ForegroundColor Cyan
Set-Location $PSScriptRoot
if (Test-Path "..\env\Scripts\streamlit.exe") {
    & ..\env\Scripts\streamlit.exe run app.py
} elseif (Test-Path ".\.venv\Scripts\streamlit.exe") {
    & .\.venv\Scripts\streamlit.exe run app.py
} elseif (Test-Path ".\venv\Scripts\streamlit.exe") {
    & .\venv\Scripts\streamlit.exe run app.py
} else {
    streamlit run app.py
}
