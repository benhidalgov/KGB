# Ficha Tecnica de Ejemplo: BALANCER001

> Juego de datos de ejemplo para el arranque de la consola en un equipo nuevo.
> No contiene informacion de produccion y puede reemplazarse sin respaldo.

## Identificacion

| Dato | Valor |
| :--- | :--- |
| Servidor | BALANCER001 |
| Numero de serie | SN-8842-A |
| Direccion IP | 10.24.0.125 |
| Maquina virtual | vm-balancer-01 |
| Capa | L4 - Balanceo |
| Componente | HAProxy 2.9 |
| Estado | Operativo |

## Descripcion general

El balanceador publica los servicios del portal en alta disponibilidad. El nodo
primario atiende el trafico y el nodo secundario permanece en espera con
sincronizacion de estado de sesion. La autenticacion de la consola administrativa
usa tokens JWT con vigencia de ocho horas.

## Procedimiento de failover

1. Confirmar la alerta en el monitoreo y verificar la salud del nodo primario.
2. Registrar el inicio de la ventana en el historial de mantenimientos.
3. Ejecutar el failover controlado y validar que el nodo secundario asuma el trafico.
4. Verificar latencia y errores durante cinco minutos.
5. Renovar el certificado o el token JWT si el procedimiento lo exige.

## Verificacion posterior

- Comprobar el estado del servicio en el monitoreo con respuesta satisfactoria.
- Confirmar que las sesiones activas se mantienen o se informa su reinicio.
- Dejar constancia en el historial de mantenimientos con fecha y responsable.
