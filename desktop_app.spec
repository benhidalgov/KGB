# -*- mode: python ; coding: utf-8 -*-
"""
Especificación de PyInstaller para Consola de Infraestructura y Operaciones.
Empaqueta la aplicación Streamlit y el runtime de PyWebView en una distribución
autocontenida para Windows.
"""
import os
import sys
from PyInstaller.utils.hooks import collect_data_files, copy_metadata, collect_submodules

block_cipher = None

# Recolección de archivos estáticos y metadatos
datas = []
datas += collect_data_files('streamlit')
datas += collect_data_files('streamlit_antd_components')
datas += collect_data_files('altair')

def safe_copy_metadata(pkg_name):
    try:
        return copy_metadata(pkg_name)
    except Exception:
        return []

datas += safe_copy_metadata('streamlit')
datas += safe_copy_metadata('google_genai')
datas += safe_copy_metadata('tqdm')
datas += safe_copy_metadata('packaging')
datas += safe_copy_metadata('requests')

# Archivos de código y estilos propios
datas += [
    ('app.py', '.'),
    ('.streamlit/config.toml', '.streamlit'),
    ('core/estilos.css', 'core'),
]

# Inclusión de módulos ocultos
hiddenimports = [
    'streamlit',
    'streamlit.web.cli',
    'streamlit.web.bootstrap',
    'streamlit.runtime.scriptrunner.magic_expressions',
    'streamlit_antd_components',
    'duckdb',
    'pandas',
    'openpyxl',
    'pypdf',
    'pdfplumber',
    'mammoth',
    'pptx',
    'cryptography',
    'webview',
    'clr',
    'pythonnet',
    'altair',
    'pydeck',
    'uvicorn',
    'starlette',
    'asyncio',
]

try:
    hiddenimports += collect_submodules('core')
    hiddenimports += collect_submodules('streamlit')
    hiddenimports += collect_submodules('streamlit_antd_components')
except Exception:
    pass

a = Analysis(
    ['desktop_app.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'notebook', 'scipy', 'unittest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='ConsolaOperaciones',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='ConsolaOperaciones',
)
