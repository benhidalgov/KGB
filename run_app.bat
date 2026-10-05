@echo off
echo Iniciando KGB - Camarada de Infraestructura y Operaciones...
cd /d "%~dp0"
if exist "..\env\Scripts\streamlit.exe" (
    call ..\env\Scripts\streamlit.exe run app.py
) else if exist ".venv\Scripts\streamlit.exe" (
    call .venv\Scripts\streamlit.exe run app.py
) else if exist "venv\Scripts\streamlit.exe" (
    call venv\Scripts\streamlit.exe run app.py
) else (
    streamlit run app.py
)
pause
