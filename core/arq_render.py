"""Render del esquema de arquitectura a un HTML autocontenido.

Consume `modelo.json` (ver `tools/gen_arq.py`) y produce el SVG con las ocho
capas, sus servicios, las flechas y el JS de foco. Sin dependencias, sin red:
todo el layout se calcula aca, el navegador solo alterna clases.
"""
import html
import json
import os

from core.configuracion import ARQ_MODELO_PATH

ANCHO = 1240
X0, ANCHO_IZQ = 30, 730
X_DER, ANCHO_DER = 820, 390
TOP = 55
ALTO_COLAPSADO = 96
SEPARACION = 20
FILA = 17
MAX_SERVICIOS = 8          # 2 columnas x 4 filas antes de resumir con "+N"
FUENTE_DER = 62            # caracteres por linea en la columna externa
FUENTE_NOTA = 66

CSS = """
  :root {
    --bg: #f7f7f5; --panel: #ffffff; --panel2: #efefea; --text: #1a1a1a; --muted: #6b6b6b;
    --line: #d8d8d4; --accent: #2f6feb; --crit: #c2410c; --int: #0f766e; --ext: #7c3aed;
  }
  html.tema-oscuro {
    --bg: #131313; --panel: #1d1d20; --panel2: #232327; --text: #e9e9e7; --muted: #9a9a98;
    --line: #34343a; --accent: #5b93ff; --crit: #fb923c; --int: #2dd4bf; --ext: #a78bfa;
  }
  body { margin: 0; height: 100vh; overflow: hidden;
         background: var(--bg); color: var(--text);
         font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif; }
  .band { fill: var(--panel); stroke: var(--line); stroke-width: 1.2; }
  .ext { stroke-dasharray: 6 4; }
  .ops { fill: var(--panel2); stroke-dasharray: 6 4; }
  .t { font-size: 19px; font-weight: 700; }
  .h { font-size: 17px; font-weight: 700; }
  .s { font-size: 11.5px; }
  .b { font-size: 11.5px; fill: var(--muted); }
  .m { font-size: 10.5px; fill: var(--muted); }
  .fl { stroke: var(--accent); stroke-width: 2; fill: none; marker-end: url(#flecha); }
  .fld { stroke: var(--muted); stroke-width: 1.4; fill: none; stroke-dasharray: 5 4; marker-end: url(#flecha-m); }
  .crit { fill: var(--crit); } .int { fill: var(--int); } .extc { fill: var(--ext); }

  /* Estado de foco: capa enfocada se agranda y centra; el resto atenua. */
  .capa { cursor: pointer; transform-box: view-box; transform-origin: 0 0;
          transition: transform .4s ease, opacity .3s ease; outline: none; }
  .capa.off { opacity: .25; }
  .capa.on .band { stroke: var(--accent); stroke-width: 2; }
  .capa:focus-visible .band { stroke: var(--accent); stroke-width: 2.5; }
  .flecha { transition: opacity .3s ease; }
  .flecha.off { opacity: .15; }
  .servicios { display: none; }
  .capa.on .servicios { display: inline; }
  .preview { display: inline; }
  .capa.on .preview { display: none; }
  svg { width: 100%; height: 100%; }

  #volver { position: fixed; top: 10px; right: 14px; display: none; z-index: 5;
            font: 600 12px/1 ui-sans-serif, system-ui, sans-serif; cursor: pointer;
            padding: 7px 12px; border-radius: 8px; border: 1px solid var(--line);
            background: var(--panel); color: var(--text); }
  body.foco #volver { display: inline-block; }
  body.foco .stamp { opacity: 0; }
  .stamp { transition: opacity .3s ease; }
  body.foco .pista { opacity: 0; }
  .pista { transition: opacity .3s ease; }
"""

JS = """
(function () {
  var capas = Array.prototype.slice.call(document.querySelectorAll('.capa'));
  var flechas = Array.prototype.slice.call(document.querySelectorAll('.flecha'));
  var activa = null;

  function ordenar() {
    var escena = document.getElementById('escena');
    capas.forEach(function (c) { escena.appendChild(c); });
    if (activa) {
      var on = capas.filter(function (c) { return c.dataset.capa === activa; })[0];
      if (on) escena.appendChild(on);
    }
  }

  function enfocar(id) {
    activa = id;
    document.body.classList.add('foco');
    capas.forEach(function (c) {
      var on = c.dataset.capa === id;
      c.classList.toggle('on', on);
      c.classList.toggle('off', !on);
      c.querySelector('rect').setAttribute('height', on ? c.dataset.h1 : c.dataset.h0);
      if (!on) c.style.transform = '';
    });
    flechas.forEach(function (f) {
      f.classList.toggle('off', f.dataset.desde !== id && f.dataset.hasta !== id);
    });
    var foco = capas.filter(function (c) { return c.dataset.capa === id; })[0];
    var b = foco.getBBox();
    var s = Math.min(1200 / b.width, 900 / b.height, 1.4);
    foco.style.transform = 'translate(' + (620 - s * (b.x + b.width / 2)) + 'px,' +
                            (480 - s * (b.y + b.height / 2)) + 'px) scale(' + s + ')';
    ordenar();
    foco.focus({ preventScroll: true });
  }

  function volver() {
    if (!activa) return;
    activa = null;
    document.body.classList.remove('foco');
    capas.forEach(function (c) {
      c.classList.remove('on', 'off');
      c.style.transform = '';
      c.querySelector('rect').setAttribute('height', c.dataset.h0);
    });
    flechas.forEach(function (f) { f.classList.remove('off'); });
    ordenar();
  }

  capas.forEach(function (c) {
    var id = c.dataset.capa;
    var accion = function () {
      if (!activa) enfocar(id);
      else if (activa !== id) volver();
    };
    c.addEventListener('click', accion);
    c.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); accion(); }
    });
  });

  document.getElementById('fondo').addEventListener('click', volver);
  document.getElementById('volver').addEventListener('click', volver);
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') volver(); });
})();
"""


def _t(texto) -> str:
    return html.escape(str(texto), quote=False)


def _n(cantidad: int, singular: str, plural: str) -> str:
    return f"{cantidad} {singular if cantidad == 1 else plural}"


def _envolver(texto: str, limite: int) -> list:
    """Corta un texto en lineas de ~limite caracteres sin partir palabras."""
    lineas, actual = [], ""
    for palabra in texto.split(" "):
        if actual and len(actual) + 1 + len(palabra) > limite:
            lineas.append(actual)
            actual = palabra
        else:
            actual = f"{actual} {palabra}".strip()
    if actual:
        lineas.append(actual)
    return [linea[2:] if linea.startswith("· ") else linea for linea in lineas]


def _badge(capa: dict) -> str:
    externos = sum(1 for s in capa["servicios"] if s["externo"])
    partes = [_n(len(capa["servicios"]), "servicio", "servicios")]
    if externos:
        partes.append(_n(externos, "externo", "externos"))
    if capa["servidores"]:
        partes.append(_n(capa["servidores"], "servidor", "servidores"))
        partes.append(_n(capa["criticos"], "crítico", "críticos"))
    elif capa["plano"] == "trafico":
        partes.append("sin servidores propios")
    return " · ".join(partes)


def _filas_servicios(capa: dict, dos_columnas: bool, maximo: int = None) -> tuple:
    """Filas de servicio en orden de lectura; el resto se resume aparte."""
    servicios = capa["servicios"]
    tope = maximo if maximo is not None else (10 if dos_columnas else 8)
    mostrados = servicios if len(servicios) <= tope else servicios[:tope]
    resto = servicios[len(mostrados):]
    filas = []
    if dos_columnas:
        for i in range(0, len(mostrados), 2):
            fila = [f"•  {_t(s['nombre'])}" for s in mostrados[i:i + 2]]
            if resto and i + 2 >= len(mostrados):
                fila[-1] += f' <tspan class="m">(+{len(resto)})</tspan>'
            filas.append(fila)
    else:
        filas = [[f"•  {_t(s['nombre'])}"] for s in mostrados]
    return filas, resto


def _lineas_resto(resto: list, dos_columnas: bool, limite: int) -> list:
    if not resto:
        return []
    resumen = " · ".join(_t(s["nombre"]) for s in resto)
    prefijo = f"+{len(resto)} más: " if dos_columnas else f"+{len(resto)} adicionales: "
    return _envolver(prefijo + resumen, limite)


def _vista_previa(capa: dict, ancho: float, alto: float, espacio: int) -> list:
    """Nombres de servicio en una linea (o varias) que se ve sin enfocar."""
    limite = max(20, int((ancho - 44) / 5.8))
    lineas = _envolver(" · ".join(s["nombre"] for s in capa["servicios"]), limite)
    maximo = max(1, int((alto - 62 - 4) // espacio))
    if len(lineas) > maximo:
        lineas = lineas[:maximo]
        lineas[-1] = lineas[-1].rstrip(" ·,") + " …"
    return lineas


def _texto(x: float, y: float, clase: str, contenido: str, extra: str = "") -> str:
    return f'      <text class="{clase}" x="{x:g}" y="{y:g}"{extra}>{contenido}</text>'


def render_html(modelo: dict) -> str:
    capas = {c["id"]: c for c in modelo["capas"]}
    hosts_por_capa = {}
    for host in modelo["hosts"]:
        hosts_por_capa.setdefault(host["capa"], []).append(host)

    # Columna izquierda: capas de trafico y gestion, apiladas.
    izquierda = [c for i, c in sorted(capas.items()) if i <= 5]
    derecha = capas[6]
    gestion = [c for i, c in sorted(capas.items()) if i >= 7]

    geometria = {}
    y = TOP
    for capa in izquierda:
        geometria[capa["id"]] = (X0, y, ANCHO_IZQ, ALTO_COLAPSADO)
        y += ALTO_COLAPSADO + SEPARACION
    fondo_izq = y - SEPARACION
    geometria[6] = (X_DER, TOP, ANCHO_DER, fondo_izq - TOP)
    y = fondo_izq + 36
    for capa in gestion:
        alto = 96 if capa["id"] == 7 else 80
        geometria[capa["id"]] = (X0, y, ANCHO - 2 * X0, alto)
        y += alto + 24
    fin = y - 24
    leyenda_y = fin + 62
    alto_svg = leyenda_y + 47

    piezas = []
    piezas.append(f'  <g id="escena">')
    piezas.append(f'    <rect id="fondo" x="0" y="0" width="{ANCHO}" height="{alto_svg}" fill="transparent"/>')
    piezas.append(_texto(X0, 30, "t", "Arquitectura de plataforma SMUCORP"))
    meta = modelo["meta"]
    piezas.append(_texto(ANCHO - 30, 28, "m stamp",
                         f"Actualizado: {_t(meta['fuente_actualizada'])} · Fuente: {_t(meta['fuente'])} "
                         f"({meta['total_servidores']} servidores · {meta['total_servicios']} servicios)",
                         ' text-anchor="end"'))

    # Flechas
    # Las relaciones de gestion se dibujan como una sola flecha hacia la capa
    # mas baja que monitorean: una por capa destino cruzaria las cajas del medio.
    gestion_destino = {}
    for rel in modelo["relaciones"]:
        if rel["tipo"] == "gestion":
            actual = gestion_destino.get(rel["desde"])
            if actual is None or geometria[rel["hasta"]][1] > geometria[actual][1]:
                gestion_destino[rel["desde"]] = rel["hasta"]

    flechas = []
    dibujadas = 0
    for rel in modelo["relaciones"]:
        desde, hasta = rel["desde"], rel["hasta"]
        if rel["tipo"] == "gestion":
            if gestion_destino[desde] != hasta:
                continue                                  # cubierta por la flecha comun
            xx = 350 + 300 * dibujadas
            y1 = geometria[desde][1] - 4
            y2 = geometria[hasta][1] + geometria[hasta][3] + 6
            cuerpo = [f'      <line class="fld" x1="{xx:g}" y1="{y1:g}" x2="{xx:g}" y2="{y2:g}"/>',
                      _texto(xx + 12, y1 - 3, "m", _t(rel["etiqueta"]))]
            dibujadas += 1
        elif hasta == 6:
            x1 = X0 + ANCHO_IZQ + 2
            x2 = X_DER - 2
            yy = geometria[desde][1] + 45
            cuerpo = [f'      <line class="fl" x1="{x1:g}" y1="{yy:g}" x2="{x2:g}" y2="{yy:g}"/>',
                      _texto((x1 + x2) / 2, yy - 7, "m", _t(rel["etiqueta"]), ' text-anchor="middle"')]
        else:
            xx = 62
            arriba = geometria[desde]
            abajo = geometria[hasta]
            y1 = arriba[1] + arriba[3] + 2
            y2 = abajo[1] - 2
            cuerpo = [f'      <line class="fl" x1="{xx:g}" y1="{y1:g}" x2="{xx:g}" y2="{y2:g}"/>',
                      _texto(xx + 12, (y1 + y2) / 2 + 4, "m", _t(rel["etiqueta"]))]
        flechas.append(f'    <g class="flecha" data-desde="{desde}" data-hasta="{hasta}">')
        flechas.extend(cuerpo)
        flechas.append("    </g>")
    piezas.extend(flechas)

    # Capas
    for capa in modelo["capas"]:
        cid = capa["id"]
        x, y0, ancho, alto = geometria[cid]
        dos_columnas = cid != 6
        espacio = FILA if dos_columnas else 18
        filas, resto = _filas_servicios(capa, dos_columnas, None if dos_columnas else len(capa["servicios"]))
        lineas_resto = _lineas_resto(resto, dos_columnas, FUENTE_NOTA if dos_columnas else FUENTE_DER)
        hosts = [h["hostname"] for h in hosts_por_capa.get(cid, [])] if capa["plano"] == "gestion" else []
        lineas_hosts = _envolver("Hosts: " + " · ".join(hosts), FUENTE_NOTA) if hosts else []
        filas_totales = max(len(filas) + len(lineas_resto),
                            len(lineas_hosts) if dos_columnas else 0)
        alto1 = max(alto, 62 + espacio * filas_totales + 10)

        clases = "band ops" if capa["plano"] == "gestion" else ("band ext" if cid == 6 else "band")
        piezas.append(f'    <g class="capa" data-capa="{cid}" data-h0="{alto}" data-h1="{alto1}" '
                      f'tabindex="0" role="button" aria-label="{_t(capa["nombre"])}, '
                      f'{_n(len(capa["servicios"]), "servicio", "servicios")}">')
        piezas.append(f'      <rect class="{clases}" x="{x:g}" y="{y0:g}" width="{ancho:g}" height="{alto:g}" rx="10"/>')
        piezas.append(_texto(x + 22, y0 + 30, "h", f'{cid} · {_t(capa["nombre"])}'))
        piezas.append(_texto(x + ancho - 22, y0 + 30, "b", _badge(capa), ' text-anchor="end"'))

        lineas_preview = _vista_previa(capa, ancho, alto, espacio)
        if lineas_preview:
            piezas.append('      <g class="preview">')
            pyy = y0 + 62
            for linea in lineas_preview:
                piezas.append(_texto(x + 22, pyy, "m", _t(linea)))
                pyy += espacio
            piezas.append("      </g>")

        piezas.append('      <g class="servicios">')
        yy = y0 + 62
        for fila in filas:
            for j, celda in enumerate(fila):
                piezas.append(_texto(x + (100 + 300 * j if dos_columnas else 22), yy, "s", celda))
            yy += espacio
        for linea in lineas_resto:
            piezas.append(_texto(x + 22, yy, "m", linea))
            yy += espacio
        if lineas_hosts:
            yy_hosts = y0 + 62
            for linea in lineas_hosts:
                piezas.append(_texto(x + 760 if dos_columnas else x + 22, yy_hosts, "m", linea))
                yy_hosts += espacio
        if cid == 6:
            piezas.append(_texto(x + 22, max(y0 + alto / 2 - 5, yy + 10), "m pista", "Clic para ampliar"))
        piezas.append("      </g>")
        piezas.append("    </g>")

    # Leyenda
    piezas.append(f'    <circle class="crit" cx="{X0 + 6:g}" cy="{leyenda_y:g}" r="5"/>')
    piezas.append(_texto(X0 + 18, leyenda_y + 4, "m", f"Servidor crítico ({meta['total_criticos']})"))
    piezas.append(f'    <circle class="int" cx="{X0 + 166:g}" cy="{leyenda_y:g}" r="5"/>')
    piezas.append(_texto(X0 + 178, leyenda_y + 4, "m", "Interno"))
    piezas.append(f'    <circle class="extc" cx="{X0 + 250:g}" cy="{leyenda_y:g}" r="5"/>')
    piezas.append(_texto(X0 + 262, leyenda_y + 4, "m", "Externo (borde punteado)"))
    piezas.append(_texto(X0 + 440, leyenda_y + 4, "m",
                         f"Mapeo de servidores por Nivel infraestructura + Sistema "
                         f"· total {meta['total_servidores']}"))
    piezas.append("  </g>")

    return (
        '<!DOCTYPE html>\n<html class="%%TEMA%%" lang="es">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Arquitectura de plataforma SMUCORP</title>\n<style>"
        f"{CSS}</style>\n</head>\n<body>\n"
        '<button id="volver" type="button" aria-label="Volver al esquema">← Volver</button>\n'
        f'<svg id="svg" viewBox="0 0 {ANCHO} {alto_svg:g}" role="img" '
        'aria-label="Esquema de arquitectura por capas">\n  <defs>\n'
        '    <marker id="flecha" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">\n'
        '      <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)"/>\n    </marker>\n'
        '    <marker id="flecha-m" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
        'markerHeight="7" orient="auto-start-reverse">\n'
        '      <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--muted)"/>\n    </marker>\n'
        f'  </defs>\n' + "\n".join(piezas) + "\n</svg>\n\n<script>" + JS + "</script>\n</body>\n</html>\n"
    )


def cargar_modelo(ruta: str = ARQ_MODELO_PATH) -> dict:
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def generar(ruta_modelo: str = ARQ_MODELO_PATH, ruta_html: str = None) -> str:
    """Escribe el HTML a partir del modelo y devuelve la ruta."""
    ruta_html = ruta_html or os.path.join(os.path.dirname(ruta_modelo), "arquitectura.html")
    contenido = render_html(cargar_modelo(ruta_modelo))
    with open(ruta_html, "w", encoding="utf-8", newline="\n") as f:
        f.write(contenido)
    return ruta_html


if __name__ == "__main__":
    print(f"[OK] {generar()}")
