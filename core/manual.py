"""
Módulo de documentación interactiva y Guía Práctica del Camarada de Infraestructura y Operaciones.
"""
import streamlit as st
import streamlit_antd_components as sac


def renderizar_manual_usuario():
    """Renderiza una guía práctica, directa y sin rodeos sobre el funcionamiento del sistema."""
    st.markdown('<p class="main-title">Guía Rápida: Cómo funciona la Consola y qué hace</p>', unsafe_allow_html=True)
    st.caption("Un resumen práctico y al grano para entender cómo sacarle provecho a la plataforma sin enredarse.")

    tab_m1, tab_m2, tab_m3, tab_m4, tab_m5, tab_m6 = st.tabs([
        "1. ¿De qué va esto?",
        "2. Cómo buscar y el Score",
        "3. Visor Lado a Lado",
        "4. Guardar cambios y Rollback",
        "5. Plantillas de Runbooks",
        "6. Carga masiva (Script)"
    ])

    # ----------------- SECCIÓN 1: ¿DE QUÉ VA ESTO? -----------------
    with tab_m1:
        st.subheader("1. ¿Qué es esta herramienta y para qué sirve?")

        st.markdown("""
En corto: es un asistente para no tener que abrir 50 carpetas compartidas ni volverse loco buscando servidores en Excels viejos.

---

### Lo que hace la herramienta por detrás:

* **Te encuentra servidores rapido:** Busca por IP (`10.24.0.125`), hostname (`BALANCER001`), número de serie (`SN-8842-A`) o técnico en la base de datos de inventario usando **DuckDB** en memoria.
* **Lee documentos por ti:** Extrae el texto de archivos PDF, Word, Excel, presentaciones y diagramas para que puedas buscar cosas como *"contingencia WSO2"* o *"autenticación JWT"* y te dé el párrafo exacto.
* **Te muestra el original y la versión limpia:** Tiene un visor de dos columnas para ver el texto indexado a la izquierda y el archivo real (el PDF embebido, el Excel en cuadrícula o la imagen) a la derecha.
* **No pierde nada (Historial y Rollback):** Cada vez que alguien edita un archivo, se guarda una versión nueva (`v1`, `v2`, `v3`). Si alguien comete un error, se vuelve a la versión anterior con un clic.
* **Genera procedimientos en 2 minutos:** Viene con formularios para redactar rollbacks, despliegues o postmortems con formato estándar.
        """)

    # ----------------- SECCIÓN 2: CÓMO BUSCAR Y EL SCORE -----------------
    with tab_m2:
        st.subheader("2. Cómo buscar cosas y qué significa el 'Score'")

        st.markdown("""
El buscador de la primera pestaña está arriba del todo y funciona tanto con términos exactos como con búsquedas generales.

---

### ¿Qué puedes escribir en la barra?
* **Datos duros de servidores:** `10.24.0.125`, `BALANCER001`, `SN-8842-A`, `VM-BOOKING-01`.
* **Conceptos técnicos y siglas:** `JWT`, `SSL`, `Redis`, `Rollback`, `Failover`, `PostgreSQL`, `Nagios`.
* **Nombres de técnicos:** `Juan Pérez`, `Carlos DevOps`.

---

### ¿Qué es el Score (puntos de coincidencia)?
El **Score** es simplemente una nota que el motor le pone a cada documento para decidir cuál mostrarte primero:

1. **Si coincide la frase exacta que escribiste:** Le suma **+30 puntos** (es casi seguro lo que buscas).
2. **Si la palabra está en el nombre del archivo:** Le suma **+20 puntos**.
3. **Por cada vez que se repite la palabra en el texto:** Suma **+2 puntos**.

* **Score alto (20 pts o más):** El documento habla directo de lo que preguntaste.
* **Score medio (menos de 20 pts):** El documento lo menciona de pasada o en un párrafo secundario.
        """)

    # ----------------- SECCIÓN 3: VISOR LADO A LADO -----------------
    with tab_m3:
        st.subheader("3. El Visor Lado a Lado: ¿Por qué dos columnas?")

        st.markdown("""
Cuando vas a la pestaña **Documentación Técnica**, puedes comparar el archivo en dos paneles paralelos:

---

### ¿Qué hay en cada columna?
* **Columna Izquierda (Versión Markdown):** Es el texto limpio y estructurado que lee el motor de búsqueda.
* **Columna Derecha (Archivo Original):** Es el documento real tal como fue subido:
  * **Si es PDF:** Te abre un lector embebido para leer, hacer zoom o imprimir.
  * **Si es Excel:** Te muestra una cuadrícula interactiva donde puedes cambiar de hoja de cálculo con un desplegable.
  * **Si es un Diagrama o Imagen (.png, .jpg, .svg):** Te muestra la imagen en grande y te deja editar el pie de imagen (*Caption*).
  * **Si es Word o PPTX:** Te da una ficha técnica con el botón para descargar el binario original.

*Tip:* Con los botones de arriba `[Lado a Lado] | [Solo Markdown] | [Solo Formato Original]` puedes ocultar una de las columnas si quieres más espacio.
        """)

    # ----------------- SECCIÓN 4: GUARDAR CAMBIOS Y ROLLBACK -----------------
    with tab_m4:
        st.subheader("4. Editar, Versionar y hacer Rollback sin miedo a romper nada")

        st.markdown("""
Aquí nada se sobreescribe a ciegas. Cualquier cambio que hagas genera una versión nueva con copia inmutable de respaldo.

---

### Reglas básicas al editar:
* **Pon quién eres y por qué cambiaste el archivo:** Para guardar cualquier cambio (en Excel, Markdown o en el pie de un diagrama), el sistema te pide obligatoriamente el **Editor / Técnico** y el **Motivo del Cambio**.
* **El sistema guarda snapshots:** En `data/history/` queda guardada la copia exacta de cómo estaba antes.

---

### ¿Cómo volver atrás si un cambio falló (Rollback)?
1. Entra al documento en **Documentación Técnica** y ve a la subpestaña **Historial de Versiones**.
2. En el desplegable, selecciona la versión vieja que quieres restaurar (ej: `v1` o `v2`).
3. Puedes usar el comparador de cambios (*Diff*) para ver exactamente qué líneas cambiaron.
4. Escribe tu nombre, la justificación del rollback y dale al botón de **Confirmar y Ejecutar Rollback**.
5. Listo: el sistema restaura el documento y crea una versión nueva registrando la reversión en el log de auditoría.
        """)

    # ----------------- SECCIÓN 5: PLANTILLAS Y RUNBOOKS -----------------
    with tab_m5:
        st.subheader("5. Plantillas: Crear procedimientos en 2 minutos")

        st.markdown("""
En la pestaña **Plantillas de documentación**, puedes redactar manuales y runbooks sin tener que preocuparte por el formato.

---

### ¿Cómo funciona?
1. **Eliges el Tipo de Procedimiento:** Ya vienen listas plantillas para Rollback de emergencia, Paso a Producción, Postmortems de incidentes P1, Fichas de APIs, Contingencias, Parchado de SO, Certificados SSL, Disaster Recovery (DRP) y Backups de BD.
2. **Llenas los campos:** Nombre del servicio, criticidad, ambiente (Producción/QA), ventana de horario y comandos.
3. **Revisas a la derecha:** Se genera la vista previa en tiempo real.
4. **Le das a Guardar:** El documento se guarda automáticamente en `data/docs/`, queda indexado como `v1` y el buscador ya puede responder sobre él.

---

### ¿Qué pasa si necesitas un tipo de documento que no existe?
* En el selector de tipo, eliges `[+ Crear Nuevo Tipo de Procedimiento...]`.
* Le pones nombre (ej: *"Procedimiento de Auditoría de Accesos"*), marcas la casilla de guardar en catálogo y listo: queda guardado en `data/plantillas_custom.json` para que tú y tu equipo lo usen cuando quieran.
        """)

    # ----------------- SECCIÓN 6: CARGA MASIVA CLI -----------------
    with tab_m6:
        st.subheader("6. Script de carga masiva (`batch_ingest.py`)")

        st.markdown(r"""
Si te pasaron una carpeta con 200 archivos o quieres sincronizar una unidad compartida de red (`Z:\`), no los subas uno a uno por la web. Usa el script de terminal:

---

### Comandos directos:

```cmd
# Opción 1: Procesa todo lo que dejes dentro de la carpeta data/inbox/
python batch_ingest.py

# Opción 2: Procesa una carpeta de red compartida (Z:\) 
python batch_ingest.py --origen Z:\Infraestructura\Manuales --workers 8
```

---

### ¿Qué hace el script?
* Revisa todas las subcarpetas.
* Calcula el hash criptográfico **SHA-256** de cada archivo: si el archivo no ha cambiado, se lo salta para no perder tiempo.
* Si es una imagen, la guarda en `data/docs/assets/` y le crea su ficha `.md`.
* Si es PDF, Word o Excel, guarda el original en `data/originals/` y genera su versión Markdown indexable en `data/docs/`.
        """)
