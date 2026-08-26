"""Modulo core del Copilot de Infraestructura y Operaciones."""

from core.topologia import TOPOLOGY_MERMAID, PLANTILLAS_DIAGRAMAS, INFRA_SPECS
from core.configuracion import (
    CSV_PATH,
    DOCS_DIR,
    ASSETS_DIR,
    ORIGINALS_DIR,
    INBOX_DIR,
    HISTORY_DIR,
    AUDIT_LOG_PATH,
    MANIFEST_PATH,
    ESTILOS_CSS_PATH,
)
from core.estilos import cargar_estilos_css
from core.auditoria import (
    obtener_historial_versiones,
    inicializar_version_inicial_si_no_existe,
    guardar_nueva_version,
    guardar_nueva_version_excel,
    obtener_contenido_version,
    obtener_bytes_snapshot,
    cargar_hoja_excel_dataframe,
    obtener_nombres_hojas_excel,
    generar_diff_texto,
    generar_diff_lado_a_lado_html,
    obtener_todos_los_eventos_auditoria,
    generar_timeline_versiones_html,
    registrar_evento_auditoria,
    obtener_fecha_carga_documento,
)
from core.motor import (
    ejecutar_consulta_sql,
    buscar_servidores_duckdb,
    buscar_en_documentos,
    generar_respuesta_asistente,
)
from core.procesador import (
    IMAGE_EXTENSIONS,
    OFFICE_EXTENSIONS,
    SUPPORTED_EXTENSIONS,
    cargar_documento_individual,
    cargar_documentos_locales,
    calcular_sha256,
    sanitizar_nombre_descarga,
    normalizar_nombre_archivo,
    normalizar_titulo_display,
    preparar_markdown_con_imagenes,
    resolver_ruta_imagen_a_base64,
    generar_ficha_diagrama,
    obtener_ruta_original,
)
from core.plantillas import (
    generar_doc_plantilla,
    obtener_todos_los_tipos_plantillas,
    cargar_plantillas_personalizadas,
    guardar_plantilla_personalizada,
)
from core.visor import (
    mostrar_pdf_embebido,
    renderizar_original_adaptativo,
    renderizar_lado_a_lado,
    renderizar_diagrama_limpio,
)
from core.manual import renderizar_manual_usuario
