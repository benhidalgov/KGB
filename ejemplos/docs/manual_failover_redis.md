# Manual de Ejemplo: Failover de la Cache Redis

> Documento de ejemplo para el arranque de la consola en un equipo nuevo.
> No contiene informacion de produccion y puede reemplazarse sin respaldo.

## Objetivo

Describir el procedimiento de failover del cluster de cache cuando un nodo
presenta latencia alta o deja de responder, causando errores en el portal.

## Sintomas observados

- Aumento sostenido de la latencia en las peticiones del portal.
- Errores 500 intermitentes en el componente que consume la cache.
- Alertas de nodo no disponible en el monitoreo central.

## Procedimiento

1. Identificar el nodo degradado y su rol dentro del cluster.
2. Ejecutar el failover para promover la replica disponible.
3. Verificar la replicacion entre los nodos restantes.
4. Reiniciar el nodo afectado fuera de la ventana de mayor demanda.
5. Registrar el evento con fecha, responsable y justificacion tecnica.

## Criterios de cierre

- Latencia del portal dentro del rango esperado.
- Sin errores 500 durante quince minutos posteriores al cambio.
- Historial de mantenimientos actualizado con el detalle del failover.
