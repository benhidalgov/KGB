FROM python:3.12-slim

# Metadatos del contenedor
LABEL maintainer="Equipo de Infraestructura y Operaciones"
LABEL description="Copilot de Infraestructura y Operaciones"

# Variables de entorno de ejecución Python y Streamlit
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    TZ=UTC \
    STREAMLIT_SERVER_PORT=8501 \
    STREAMLIT_SERVER_ADDRESS=0.0.0.0 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Instalar dependencias del sistema operativo (curl para el healthcheck, gosu para bajar privilegios, tzdata para TZ)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gosu \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# Usuario sin privilegios para ejecutar el servicio
RUN useradd --create-home --uid 10001 --shell /usr/sbin/nologin appuser

# Copiar manifiesto de dependencias e instalar.
# pyinstaller y pywebview son exclusivos del empaquetado de escritorio (.exe)
# en Windows; no aplican a la imagen Linux.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    grep -vE '^(pyinstaller|pywebview)==' requirements.txt > /tmp/requirements-docker.txt && \
    pip install --no-cache-dir -r /tmp/requirements-docker.txt

# Copiar código fuente del proyecto y fijar propiedad
COPY . .
RUN chown -R appuser:appuser /app

# Directorio de datos persistente creado en la imagen con el dueño correcto,
# para que un volumen nombrado herede la propiedad. Con bind-mount, el
# entrypoint corrige la propiedad del punto de montaje antes de servir.
RUN mkdir -p /app/data/docs/assets /app/data/originals /app/data/inbox /app/data/history \
    && chown -R appuser:appuser /app/data
RUN sed -i 's/\r$//' /app/docker/entrypoint.sh && chmod +x /app/docker/entrypoint.sh

# Exponer puerto predeterminado de Streamlit
EXPOSE 8501

# Verificación de salud interna del contenedor
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# El entrypoint arranca como root, corrige la propiedad de /app/data y luego
# baja a appuser antes de ejecutar el comando del servicio.
ENTRYPOINT ["/app/docker/entrypoint.sh"]

# Comando de inicio del servicio
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
