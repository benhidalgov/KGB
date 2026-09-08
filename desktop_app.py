"""
Lanzador de Escritorio para la Consola de Infraestructura y Operaciones.
Inicia el backend de Streamlit en segundo plano y abre una ventana nativa
de escritorio (Edge WebView2) mediante PyWebView, con fallback automático.
"""
import os
import sys
import time
import socket
import urllib.request
import threading
import subprocess
import webbrowser

# ---------------------------------------------------------------------------
# 1. RESOLUCIÓN DE RUTAS SEGURAS (Soporte PyInstaller Frozen vs Desarrollo)
# ---------------------------------------------------------------------------
if getattr(sys, 'frozen', False):
    # Ejecutándose como binario empaquetado (.exe)
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, '_MEIPASS', APP_DIR)
    try:
        os.chdir(APP_DIR)
    except Exception:
        pass
else:
    # Ejecutándose como script en desarrollo
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR

# Ruta del script principal de Streamlit
APP_SCRIPT = os.path.join(BUNDLE_DIR, "app.py")
if not os.path.exists(APP_SCRIPT):
    APP_SCRIPT = os.path.join(APP_DIR, "app.py")

DATA_DIR = os.path.join(APP_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, ".webview_cache")
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(CACHE_DIR, exist_ok=True)


# ---------------------------------------------------------------------------
# 2. LOCALIZACIÓN DE PUERTO Y SALUD DEL SERVIDOR
# ---------------------------------------------------------------------------
def obtener_puerto_disponible(puerto_inicial: int = 8501) -> int:
    """Encuentra un puerto TCP libre en 127.0.0.1 a partir de puerto_inicial."""
    for p in range(puerto_inicial, puerto_inicial + 100):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.3)
            if s.connect_ex(('127.0.0.1', p)) != 0:
                return p
    return puerto_inicial


def esperar_servidor_listo(puerto: int, max_segundos: float = 30.0) -> bool:
    """Monitorea el endpoint de salud de Streamlit hasta que responda HTTP 200."""
    url = f"http://127.0.0.1:{puerto}/_stcore/health"
    t_fin = time.time() + max_segundos
    while time.time() < t_fin:
        try:
            with urllib.request.urlopen(url, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


# ---------------------------------------------------------------------------
# 3. LANZAMIENTO DEL BACKEND STREAMLIT
# ---------------------------------------------------------------------------
def iniciar_servidor_streamlit(puerto: int):
    """Inicia el servidor Streamlit en un hilo daemon."""
    import streamlit.config as config
    import streamlit.web.bootstrap as bootstrap

    # Desactivar registro de señales del sistema (evita ValueError en hilos secundarios)
    bootstrap._set_up_signal_handler = lambda server: None

    # Configuración del servidor
    config.set_option("server.port", puerto)
    config.set_option("server.address", "127.0.0.1")
    config.set_option("server.headless", True)
    config.set_option("server.enableCORS", False)
    config.set_option("server.enableXsrfProtection", False)
    config.set_option("browser.gatherUsageStats", False)
    config.set_option("browser.serverAddress", "127.0.0.1")
    config.set_option("global.developmentMode", False)

    bootstrap.run(APP_SCRIPT, False, [], {})


# ---------------------------------------------------------------------------
# 4. VENTANA DE ESCRITORIO (PYWEBVIEW CON FALLBACK)
# ---------------------------------------------------------------------------
def abrir_ventana_escritorio(url: str):
    """Abre una ventana nativa de escritorio o recurre a modo aplicación de Edge."""
    try:
        import webview

        def al_cerrar():
            # Termina el proceso limpiamente al cerrar la ventana nativa
            os._exit(0)

        ventana = webview.create_window(
            title="Consola de Infraestructura y Operaciones",
            url=url,
            width=1400,
            height=900,
            min_size=(1024, 680),
            confirm_close=False,
            background_color="#0F172A",
            text_select=True,
        )
        ventana.events.closed += al_cerrar

        # Iniciar loop nativo de PyWebView con persistencia de cookies en CACHE_DIR
        webview.start(storage_path=CACHE_DIR)
        os._exit(0)

    except Exception as e_wv:
        print(f"[WARN] No se pudo abrir ventana con PyWebView ({e_wv}). Usando fallback...")

        # Fallback 1: Microsoft Edge en modo aplicación (ventana nativa sin URL ni pestañas)
        try:
            cmd = ["msedge.exe", f"--app={url}", "--window-size=1400,900"]
            proc = subprocess.Popen(cmd)
            proc.wait()
            os._exit(0)
        except Exception:
            pass

        # Fallback 2: Navegador predeterminado
        webbrowser.open(url)
        # Mantener el proceso vivo
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            os._exit(0)


# ---------------------------------------------------------------------------
# 5. PUNTO DE ENTRADA PRINCIPAL
# ---------------------------------------------------------------------------
def main():
    puerto = obtener_puerto_disponible(8501)
    print(f"[*] Iniciando servidor local en http://127.0.0.1:{puerto}...")

    # Arrancar Streamlit en segundo plano
    t_st = threading.Thread(target=iniciar_servidor_streamlit, args=(puerto,), daemon=True)
    t_st.start()

    # Esperar hasta que el servidor responda
    if not esperar_servidor_listo(puerto, max_segundos=35.0):
        print("[ERROR] El servidor Streamlit tardó demasiado en responder.")
        sys.exit(1)

    print("[*] Servidor en línea. Abriendo ventana de escritorio...")
    app_url = f"http://127.0.0.1:{puerto}"
    abrir_ventana_escritorio(app_url)


if __name__ == "__main__":
    main()
