#!/bin/sh
# Entrypoint de la Consola de Infraestructura y Operaciones.
#
# El bind-mount ./data:/app/data hereda el UID del host, que normalmente no es
# el del usuario sin privilegios del contenedor (10001). Si el contenedor arranca
# como root, se ajusta la propiedad del punto de montaje y luego se bajan los
# privilegios antes de ejecutar el servicio.
set -e

if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/data/docs/assets /app/data/originals /app/data/inbox /app/data/history
    # ponytail: chown recursivo en cada arranque. Con un volumen documental muy
    # grande, limitarlo a las rutas escribibles o usar un volumen nombrado.
    # Sin cambio: el costo es por archivo, no por byte (medido 2026-11:
    # 161 archivos / 1.3 GB, milisegundos). Revisar al pasar de ~10.000 archivos;
    # el salto de fondo es el volumen nombrado, decision de despliegue.
    chown -R appuser:appuser /app/data
    export HOME=/home/appuser
    exec gosu appuser "$@"
fi

exec "$@"
