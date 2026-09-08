@echo off
setlocal enabledelayedexpansion

echo =========================================================================
echo   Compilador de Aplicacion de Escritorio (.exe)
echo   Consola de Infraestructura y Operaciones
echo =========================================================================
echo.

cd /d "%~dp0"

:: Detectar entorno virtual
set "PY_EXE="
if exist "..\env\Scripts\python.exe" set "PY_EXE=..\env\Scripts\python.exe"
if exist ".venv\Scripts\python.exe" set "PY_EXE=.venv\Scripts\python.exe"
if "%PY_EXE%"=="" set "PY_EXE=python"

echo [*] Interprete de Python: %PY_EXE%

echo [*] Compilando con PyInstaller (desktop_app.spec)...
%PY_EXE% -m PyInstaller desktop_app.spec --noconfirm --clean

if %ERRORLEVEL% neq 0 (
    echo [ERROR] La compilacion ha fallado.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [*] Estructurando directorio de datos persistentes en dist\ConsolaOperaciones...

%PY_EXE% -c "import os, shutil; d=os.path.join('dist','ConsolaOperaciones','data'); [os.makedirs(os.path.join(d, s), exist_ok=True) for s in ['docs', os.path.join('docs','assets'), 'history', 'inbox', 'originals']]; os.makedirs(os.path.join('dist','ConsolaOperaciones','.streamlit'), exist_ok=True); [shutil.copy2(src, dst) for src, dst in [('data/mantenimientos.csv', os.path.join(d,'mantenimientos.csv')), ('data/categorias.json', os.path.join(d,'categorias.json')), ('data/users.json', os.path.join(d,'users.json')), ('.streamlit/config.toml', os.path.join('dist','ConsolaOperaciones','.streamlit','config.toml'))] if os.path.exists(src)]"


echo.
echo =========================================================================
echo   [OK] Compilacion completada con exito!
echo   La aplicacion se encuentra lista en:
echo   dist\ConsolaOperaciones\ConsolaOperaciones.exe
echo =========================================================================
echo.
pause
