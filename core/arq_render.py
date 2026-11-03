"""Render del esquema de arquitectura a un HTML autocontenido.

Consume `modelo.json` (ver `tools/gen_arq.py`) y produce dos vistas del mismo
modelo, conmutables por pestañas sin recargar:

- Capas: las ocho capas apiladas, con foco por click y vista previa.
- Flujo: los flujos transaccionales como filas y las capas como columnas.

Todo el layout se calcula aca y las flechas se rutean en ortogonal desde el
borde de una caja al de la siguiente. Sin dependencias, sin red.
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

# Vista de flujo
COL_X0, COL_W = 40, 200     # columna de cada capa (1..6)
NODO_W, NODO_H = 140, 42
FILA_FLUJO = 112
TOP_FLUJO = 96
FUENTE_NODO = 20

CSS = """
  :root {
    --bg: #f5f6f8; --panel: #ffffff; --panel2: #eef0f4; --text: #14161a; --muted: #666d78;
    --line: #dce0e6; --accent: #2563eb; --crit: #b45309; --int: #0f766e; --ext: #6d28d9;
    --mono: ui-monospace, "Cascadia Mono", Consolas, monospace;
    --dur-rapida: .16s; --dur-media: .28s; --ease: cubic-bezier(.2, .6, .2, 1);
  }
  html.tema-oscuro {
    --bg: #101215; --panel: #181b1f; --panel2: #21252b; --text: #e8eaed; --muted: #8d949e;
    --line: #2c3138; --accent: #6ea0ff; --crit: #fb923c; --int: #2dd4bf; --ext: #a78bfa;
  }
  body { margin: 0; height: 100vh; overflow: hidden; display: flex; flex-direction: column;
         background: var(--bg); color: var(--text);
         font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif; }
  svg.vista { flex: 1 1 auto; width: 100%; min-height: 0; cursor: grab; }
  body.arrastrando svg.vista { cursor: grabbing; }
  body.arrastrando { user-select: none; }
  #escena, #escena-flujo { transform-box: view-box; transform-origin: 0 0; }
  svg text { fill: var(--text); }
  svg[hidden] { display: none; }

  /* Movimiento: solo lo que explica algo. Una curva, dos duraciones. */
  @keyframes aparecer { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
  @keyframes trazar { from { stroke-dashoffset: 1000; } to { stroke-dashoffset: 0; } }
  .servicios, .preview { animation: aparecer var(--dur-media) var(--ease) both; }
  .flujo.on .paso { animation: aparecer var(--dur-rapida) var(--ease) both;
                    animation-delay: calc(var(--i, 0) * 45ms); }
  .flujo.on .ff { animation: trazar var(--dur-media) var(--ease) both;
                  stroke-dasharray: 1000; }
  .band, .fila, .nodo { transition: fill var(--dur-rapida) var(--ease),
                                   stroke var(--dur-rapida) var(--ease); }
  .capa:not(.off):hover .band, .flujo:not(.off):hover .fila { fill: var(--panel2); }
  @media (prefers-reduced-motion: reduce) {
    .servicios, .preview, .flujo.on .paso, .flujo.on .ff { animation: none; }
    .capa, .flecha, .flujo, .band, .fila, .nodo { transition: none; }
  }

  #tabs { display: flex; align-items: center; gap: 22px; padding: 14px 0 0 30px; }
  .tab { font: 500 13px/1 inherit; cursor: pointer; padding: 0 0 7px; border: 0;
         background: none; color: var(--muted); border-bottom: 2px solid transparent; }
  .tab[aria-selected="true"] { color: var(--text); border-bottom-color: var(--accent); }
  .tab:focus-visible { outline: 2px solid var(--accent); outline-offset: 3px; border-radius: 3px; }

  .band { fill: var(--panel); stroke: var(--line); stroke-width: 1.2; }
  .ext { stroke-dasharray: 6 4; }
  .ops { fill: var(--panel2); stroke-dasharray: 6 4; }
  .regla { stroke: var(--line); stroke-width: 1; }
  .t { font-size: 22px; font-weight: 600; letter-spacing: -.01em; }
  .h { font-size: 16px; font-weight: 600; }
  .f { font-size: 13px; font-weight: 600; }
  .s { font-size: 11.5px; }
  .b { font-size: 11px; fill: var(--muted); }
  .m { font-size: 10.5px; fill: var(--muted); }
  .d { font-size: 10px; fill: var(--muted); }
  .idx { font-family: var(--mono); font-size: 11px; font-weight: 500; fill: var(--muted); }
  .stamp { font-family: var(--mono); font-size: 10px; }
  .capa.on .idx { fill: var(--accent); }
  .fl { stroke: var(--accent); stroke-width: 1.8; fill: none; marker-end: url(#flecha-c); }
  .fld { stroke: var(--muted); stroke-width: 1.3; fill: none; stroke-dasharray: 5 4; marker-end: url(#flecha-cm); }
  .ff { stroke: var(--accent); stroke-width: 1.5; fill: none; marker-end: url(#flecha-f); }
  .crit { fill: var(--crit); } .int { fill: var(--int); } .extc { fill: var(--ext); }

  /* Foco por capa */
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

  /* Foco por flujo */
  .flujo { cursor: pointer; transition: opacity .3s ease; outline: none; }
  .flujo.off { opacity: .2; }
  .flujo.on .fila { stroke: var(--accent); stroke-width: 2; }
  .flujo:focus-visible .fila { stroke: var(--accent); stroke-width: 2.5; }
  .fila { fill: var(--panel); stroke: var(--line); stroke-width: 1.2; }
  .nodo { fill: var(--panel2); stroke: var(--line); stroke-width: 1.2; }
  .flujo.on .nodo { stroke: var(--accent); }

  #volver { position: fixed; top: 10px; right: 14px; display: none; z-index: 5;
            font: 600 12px/1 inherit; cursor: pointer;
            padding: 7px 12px; border-radius: 8px; border: 1px solid var(--line);
            background: var(--panel); color: var(--text); }
  body.foco #volver { display: inline-block; }
  body.foco .stamp { opacity: 0; }
  .stamp { transition: opacity .3s ease; }
  body.foco .leyenda { opacity: 0; }
  .leyenda { transition: opacity .3s ease; }
  body.foco .pista { opacity: 0; }
  .pista { transition: opacity .3s ease; }
"""

JS = """
(function () {
  var cuerpo = document.body;
  var tabs = Array.prototype.slice.call(document.querySelectorAll('.tab'));
  var vistaCapas = document.getElementById('vista-capas');
  var vistaFlujo = document.getElementById('vista-flujo');
  var capas = Array.prototype.slice.call(vistaCapas.querySelectorAll('.capa'));
  var flechas = Array.prototype.slice.call(vistaCapas.querySelectorAll('.flecha'));
  var flujos = Array.prototype.slice.call(vistaFlujo.querySelectorAll('.flujo'));
  var escenas = [document.getElementById('escena'), document.getElementById('escena-flujo')];
  var capaActiva = null, flujoActivo = null;
  var zoom = { s: 1, x: 0, y: 0 };
  var arrastre = null, movido = false, suprimir = false;

  function aplicarZoom() {
    escenas.forEach(function (e) {
      e.style.transform = zoom.s === 1 ? '' :
        'translate(' + zoom.x + 'px,' + zoom.y + 'px) scale(' + zoom.s + ')';
    });
  }

  function resetZoom() {
    zoom.s = 1; zoom.x = 0; zoom.y = 0;
    aplicarZoom();
  }

  function punto(e, svg) {
    var vb = svg.viewBox.baseVal, r = svg.getBoundingClientRect();
    var k = Math.min(r.width / vb.width, r.height / vb.height);
    var ox = r.left + (r.width - vb.width * k) / 2;
    var oy = r.top + (r.height - vb.height * k) / 2;
    return { x: (e.clientX - ox) / k, y: (e.clientY - oy) / k };
  }

  function escalaDe(svg) {
    var vb = svg.viewBox.baseVal, r = svg.getBoundingClientRect();
    return Math.min(r.width / vb.width, r.height / vb.height);
  }

  function fijar(svg) {
    var vb = svg.viewBox.baseVal;
    zoom.x = Math.min(0, Math.max(vb.width * (1 - zoom.s), zoom.x));
    zoom.y = Math.min(0, Math.max(vb.height * (1 - zoom.s), zoom.y));
  }

  function alRodar(e, svg) {
    if (capaActiva) return;
    e.preventDefault();
    var p = punto(e, svg);
    var nuevo = Math.min(3, Math.max(1, zoom.s * (e.deltaY < 0 ? 1.12 : 1 / 1.12)));
    zoom.x += p.x * (zoom.s - nuevo);
    zoom.y += p.y * (zoom.s - nuevo);
    zoom.s = nuevo;
    fijar(svg);
    aplicarZoom();
  }

  function alPresionar(e, svg) {
    if (capaActiva || e.button !== 0) return;
    suprimir = false; movido = false;
    arrastre = { svg: svg, x: e.clientX, y: e.clientY, tx: zoom.x, ty: zoom.y };
    cuerpo.classList.add('arrastrando');
  }

  function alMover(e) {
    if (!arrastre) return;
    if (zoom.s === 1) return;                         // sin zoom no hay nada que mover
    if (Math.abs(e.clientX - arrastre.x) + Math.abs(e.clientY - arrastre.y) > 4) movido = true;
    if (!movido) return;
    var k = escalaDe(arrastre.svg);
    zoom.x = arrastre.tx + (e.clientX - arrastre.x) / k;
    zoom.y = arrastre.ty + (e.clientY - arrastre.y) / k;
    fijar(arrastre.svg);
    aplicarZoom();
  }

  function alSoltar() {
    if (!arrastre) return;
    arrastre = null;
    cuerpo.classList.remove('arrastrando');
    if (movido) { suprimir = true; setTimeout(function () { suprimir = false; }, 0); }
  }

  // Alinea las pestanas con el borde del contenido: el SVG se centra con
  // letterboxing, asi que su caja no coincide con el viewBox.
  function alinear() {
    var svg = cuerpo.dataset.vista === 'flujo' ? vistaFlujo : vistaCapas;
    var r = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
    if (!r.width || !r.height) return;
    var k = Math.min(r.width / vb.width, r.height / vb.height);
    var izq = r.left + (r.width - vb.width * k) / 2;
    document.getElementById('tabs').style.paddingLeft = Math.max(8, izq + 30 * k) + 'px';
  }

  function ordenar() {
    var escena = document.getElementById('escena');
    capas.forEach(function (c) { escena.appendChild(c); });
    if (capaActiva) {
      var on = capas.filter(function (c) { return c.dataset.capa === capaActiva; })[0];
      if (on) escena.appendChild(on);
    }
  }

  function enfocar(id) {
    resetZoom();
    capaActiva = id;
    cuerpo.classList.add('foco');
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
    var svg = foco.closest('svg'), vb = svg.viewBox.baseVal;
    var k = escalaDe(svg);
    var aw = Math.min(vb.width, svg.clientWidth / k);    // area visible en unidades del viewBox
    var ah = Math.min(vb.height, svg.clientHeight / k);
    var s = Math.min(aw * .92 / b.width, ah * .92 / b.height, 1.4);
    foco.style.transform = 'translate(' + (vb.width / 2 - s * (b.x + b.width / 2)) + 'px,' +
                            (ah / 2 - s * (b.y + b.height / 2)) + 'px) scale(' + s + ')';
    ordenar();
    foco.focus({ preventScroll: true });
  }

  function volver() {
    resetZoom();
    if (!capaActiva) return;
    capaActiva = null;
    cuerpo.classList.remove('foco');
    capas.forEach(function (c) {
      c.classList.remove('on', 'off');
      c.style.transform = '';
      c.querySelector('rect').setAttribute('height', c.dataset.h0);
    });
    flechas.forEach(function (f) { f.classList.remove('off'); });
    ordenar();
  }

  function limpiarFlujos() {
    if (!flujoActivo) return;
    flujoActivo = null;
    flujos.forEach(function (f) { f.classList.remove('on', 'off'); });
  }

  function enfocarFlujo(id) {
    flujoActivo = id;
    flujos.forEach(function (f) {
      var on = f.dataset.flujo === id;
      f.classList.toggle('on', on);
      f.classList.toggle('off', !on);
    });
  }

  capas.forEach(function (c) {
    var id = c.dataset.capa;
    var accion = function () {
      if (suprimir) return;
      if (!capaActiva) enfocar(id);
      else if (capaActiva !== id) volver();
    };
    c.addEventListener('click', accion);
    c.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); accion(); }
    });
  });

  flujos.forEach(function (f) {
    var id = f.dataset.flujo;
    var accion = function () {
      if (suprimir) return;
      if (flujoActivo === id) limpiarFlujos();
      else enfocarFlujo(id);
    };
    f.addEventListener('click', accion);
    f.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); accion(); }
    });
  });

  document.getElementById('fondo-capas').addEventListener('click', function () {
    if (!suprimir) volver();
  });
  document.getElementById('fondo-flujo').addEventListener('click', function () {
    if (!suprimir) limpiarFlujos();
  });
  document.getElementById('volver').addEventListener('click', volver);
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { volver(); limpiarFlujos(); }
  });

  [vistaCapas, vistaFlujo].forEach(function (svg) {
    svg.addEventListener('wheel', function (e) { alRodar(e, svg); }, { passive: false });
    svg.addEventListener('pointerdown', function (e) { alPresionar(e, svg); });
  });
  window.addEventListener('pointermove', alMover);
  window.addEventListener('pointerup', alSoltar);
  window.addEventListener('pointercancel', alSoltar);

  tabs.forEach(function (t) {
    t.addEventListener('click', function () {
      var vista = t.dataset.vista;
      cuerpo.dataset.vista = vista;
      tabs.forEach(function (o) { o.setAttribute('aria-selected', o === t ? 'true' : 'false'); });
      vistaCapas.toggleAttribute('hidden', vista !== 'capas');
      vistaFlujo.toggleAttribute('hidden', vista !== 'flujo');
      volver();
      limpiarFlujos();
      alinear();
    });
  });
  window.addEventListener('resize', alinear);
  alinear();
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


def _ruta(x1: float, y1: float, x2: float, y2: float) -> str:
    """Recorrido ortogonal entre dos puntos (recta si comparten eje)."""
    if abs(y1 - y2) < 0.5:
        return f"M {x1:g} {y1:g} H {x2:g}"
    if abs(x1 - x2) < 0.5:
        return f"M {x1:g} {y1:g} V {y2:g}"
    medio = (x1 + x2) / 2
    return f"M {x1:g} {y1:g} H {medio:g} V {y2:g} H {x2:g}"


def _texto(x: float, y: float, clase: str, contenido: str, extra: str = "") -> str:
    return f'      <text class="{clase}" x="{x:g}" y="{y:g}"{extra}>{contenido}</text>'


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


def _recortar(texto: str, limite: int) -> str:
    """Recorta a `limite` caracteres con elipsis, sin partir la ultima palabra."""
    if len(texto) <= limite:
        return texto
    corte = texto[:limite - 1].rsplit(" ", 1)[0] or texto[:limite - 1]
    return corte.rstrip(" ,;.") + "…"


def _filas_servicios(capa: dict, dos_columnas: bool, maximo: int = None) -> tuple:
    """Filas de servicio en orden de lectura; el resto se resume aparte."""
    servicios = capa["servicios"]
    tope = maximo if maximo is not None else (10 if dos_columnas else 8)
    mostrados = servicios if len(servicios) <= tope else servicios[:tope]
    resto = servicios[len(mostrados):]
    if dos_columnas:
        filas = [mostrados[i:i + 2] for i in range(0, len(mostrados), 2)]
    else:
        filas = [[s] for s in mostrados]
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


def _titulo(modelo: dict) -> list:
    meta = modelo["meta"]
    return [
        _texto(X0, 30, "t", "Arquitectura de plataforma SMUCORP"),
        _texto(ANCHO - 30, 28, "m stamp",
               f"Actualizado: {_t(meta['fuente_actualizada'])} · "
               f"Fuente: {_t(meta['fuente'])} ({meta['total_servidores']} servidores · "
               f"{meta['total_servicios']} servicios)", ' text-anchor="end"'),
    ]


def _svg_capas(modelo: dict) -> tuple:
    capas = {c["id"]: c for c in modelo["capas"]}
    hosts_por_capa = {}
    for host in modelo["hosts"]:
        hosts_por_capa.setdefault(host["capa"], []).append(host)

    izquierda = [c for i, c in sorted(capas.items()) if i <= 5]
    gestion = [c for i, c in sorted(capas.items()) if i >= 7]

    geometria = {}
    y = TOP
    for capa in izquierda:
        geometria[capa["id"]] = (X0, y, ANCHO_IZQ, ALTO_COLAPSADO)
        y += ALTO_COLAPSADO + SEPARACION
    fondo_izq = y - SEPARACION
    # La columna externa solo baja hasta la ultima capa que la llama: estirarla
    # hasta el batch deja media caja vacia.
    fin_ext = geometria[4][1] + geometria[4][3] + 24
    geometria[6] = (X_DER, TOP, ANCHO_DER, fin_ext - TOP)
    y = fondo_izq + 36
    for capa in gestion:
        alto = 96 if capa["id"] == 7 else 80
        geometria[capa["id"]] = (X0, y, ANCHO - 2 * X0, alto)
        y += alto + 24
    fin = y - 24
    leyenda_y = fin + 62
    alto_svg = leyenda_y + 47

    piezas = ['  <g id="escena">',
              f'    <rect id="fondo-capas" x="0" y="0" width="{ANCHO}" height="{alto_svg}" fill="transparent"/>']
    piezas.extend(_titulo(modelo))

    # Las relaciones de gestion se dibujan como una sola flecha hacia la capa
    # mas baja que monitorean: una por capa destino cruzaria las cajas del medio.
    gestion_destino = {}
    for rel in modelo["relaciones"]:
        if rel["tipo"] == "gestion":
            actual = gestion_destino.get(rel["desde"])
            if actual is None or geometria[rel["hasta"]][1] > geometria[actual][1]:
                gestion_destino[rel["desde"]] = rel["hasta"]

    dibujadas = 0
    for rel in modelo["relaciones"]:
        desde, hasta = rel["desde"], rel["hasta"]
        if rel["tipo"] == "gestion":
            if gestion_destino[desde] != hasta:
                continue                                  # cubierta por la flecha comun
            xx = 350 + 300 * dibujadas
            y1 = geometria[desde][1] - 4
            y2 = geometria[hasta][1] + geometria[hasta][3] + 6
            cuerpo = [f'      <path class="fld" d="{_ruta(xx, y1, xx, y2)}"/>',
                      _texto(xx + 12, y1 - 3, "m", _t(rel["etiqueta"]))]
            dibujadas += 1
        elif hasta == 6:
            x1 = X0 + ANCHO_IZQ + 2
            x2 = X_DER - 2
            yy = geometria[desde][1] + 45
            cuerpo = [f'      <path class="fl" d="{_ruta(x1, yy, x2, yy)}"/>',
                      _texto((x1 + x2) / 2, yy - 7, "m", _t(rel["etiqueta"]), ' text-anchor="middle"')]
        else:
            xx = 62
            arriba, abajo = geometria[desde], geometria[hasta]
            y1 = arriba[1] + arriba[3] + 2
            y2 = abajo[1] - 2
            cuerpo = [f'      <path class="fl" d="{_ruta(xx, y1, xx, y2)}"/>',
                      _texto(xx + 12, (y1 + y2) / 2 + 4, "m", _t(rel["etiqueta"]))]
        piezas.append(f'    <g class="flecha" data-desde="{desde}" data-hasta="{hasta}">')
        piezas.extend(cuerpo)
        piezas.append("    </g>")

    for capa in modelo["capas"]:
        cid = capa["id"]
        x, y0, ancho, alto = geometria[cid]
        dos_columnas = cid != 6
        espacio = FILA if dos_columnas else 18
        filas, resto = _filas_servicios(capa, dos_columnas, None if dos_columnas else len(capa["servicios"]))
        lineas_resto = _lineas_resto(resto, dos_columnas, FUENTE_NOTA if dos_columnas else FUENTE_DER)
        hosts = [h["hostname"] for h in hosts_por_capa.get(cid, [])] if capa["plano"] == "gestion" else []
        lineas_hosts = _envolver("Hosts: " + " · ".join(hosts), FUENTE_NOTA) if hosts else []
        paso = espacio + 14                              # nombre + descripcion
        alto_srv = 62 + paso * len(filas) + espacio * len(lineas_resto) + 10
        alto_hosts = 62 + espacio * len(lineas_hosts) + 10 if lineas_hosts else 0
        alto1 = max(ALTO_COLAPSADO, alto_srv, alto_hosts)

        clases = "band ops" if capa["plano"] == "gestion" else ("band ext" if cid == 6 else "band")
        piezas.append(f'    <g class="capa" data-capa="{cid}" data-h0="{alto}" data-h1="{alto1}" '
                      f'tabindex="0" role="button" aria-label="{_t(capa["nombre"])}, '
                      f'{_n(len(capa["servicios"]), "servicio", "servicios")}">')
        piezas.append(f'      <rect class="{clases}" x="{x:g}" y="{y0:g}" width="{ancho:g}" height="{alto:g}" rx="8"/>')
        piezas.append(_texto(x + 22, y0 + 30, "h",
                             f'<tspan class="idx">{cid:02d}</tspan>   {_t(capa["nombre"])}'))
        piezas.append(_texto(x + ancho - 22, y0 + 30, "b", _badge(capa), ' text-anchor="end"'))
        piezas.append(f'      <line class="regla" x1="{x + 16:g}" y1="{y0 + 44:g}" '
                      f'x2="{x + ancho - 16:g}" y2="{y0 + 44:g}"/>')

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
        for fi, fila in enumerate(filas):
            for j, servicio in enumerate(fila):
                cx = x + (100 + 300 * j if dos_columnas else 22)
                marca = ""
                if resto and fi == len(filas) - 1 and j == len(fila) - 1:
                    marca = f' <tspan class="m">(+{len(resto)})</tspan>'
                piezas.append(_texto(cx, yy, "s", f"•  {_t(servicio['nombre'])}{marca}"))
                if servicio.get("descripcion"):
                    piezas.append(_texto(cx + 18, yy + 13, "d",
                                         _t(_recortar(servicio["descripcion"], 54 if dos_columnas else 64))))
            yy += paso
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

    meta = modelo["meta"]
    piezas.append('    <g class="leyenda">')
    piezas.append(f'    <circle class="crit" cx="{X0 + 6:g}" cy="{leyenda_y:g}" r="5"/>')
    piezas.append(_texto(X0 + 18, leyenda_y + 4, "m", f"Servidor crítico ({meta['total_criticos']})"))
    piezas.append(f'    <circle class="int" cx="{X0 + 166:g}" cy="{leyenda_y:g}" r="5"/>')
    piezas.append(_texto(X0 + 178, leyenda_y + 4, "m", "Interno"))
    piezas.append(f'    <circle class="extc" cx="{X0 + 250:g}" cy="{leyenda_y:g}" r="5"/>')
    piezas.append(_texto(X0 + 262, leyenda_y + 4, "m", "Externo (borde punteado)"))
    piezas.append(_texto(X0 + 440, leyenda_y + 4, "m",
                         f"Mapeo de servidores por Nivel infraestructura + Sistema "
                         f"· total {meta['total_servidores']}"))
    piezas.append(_texto(ANCHO - 30, leyenda_y + 4, "m",
                         "Clic para enfocar · Rueda: zoom · Arrastrá: mover · Esc: volver",
                         ' text-anchor="end"'))
    piezas.append("    </g>")
    piezas.append("  </g>")
    return piezas, alto_svg


def _svg_flujo(modelo: dict) -> tuple:
    capas = {c["id"]: c for c in modelo["capas"]}
    columnas = [i for i in sorted(capas) if capas[i]["plano"] != "gestion"]
    alto_svg = TOP_FLUJO + FILA_FLUJO * len(modelo["flujos"]) + 34

    piezas = ['  <g id="escena-flujo">',
              f'    <rect id="fondo-flujo" x="0" y="0" width="{ANCHO}" height="{alto_svg}" fill="transparent"/>']
    piezas.extend(_titulo(modelo))

    for capa_id in columnas:
        x = COL_X0 + (capa_id - 1) * COL_W
        for i, linea in enumerate(_envolver(capas[capa_id]["nombre"], 30)[:2]):
            indice = f'<tspan class="idx">{capa_id:02d}</tspan>  ' if i == 0 else ""
            piezas.append(_texto(x, 66 + 14 * i, "b", indice + _t(linea).replace("·", "")))

    for k, flujo in enumerate(modelo["flujos"]):
        y0 = TOP_FLUJO + k * FILA_FLUJO
        centro = y0 + (FILA_FLUJO - 18) / 2 + 12
        piezas.append(f'    <g class="flujo" data-flujo="{flujo["id"]}" tabindex="0" role="button" '
                      f'aria-label="Flujo {_t(flujo["nombre"])}">')
        piezas.append(f'      <rect class="fila" x="20" y="{y0:g}" width="1200" height="{FILA_FLUJO - 18}" rx="8"/>')
        piezas.append(_texto(36, y0 + 20, "f", _t(flujo["nombre"])))

        conteo, posiciones = {}, []
        for paso in flujo["pasos"]:
            conteo[paso["capa"]] = conteo.get(paso["capa"], 0) + 1
            posiciones.append((paso, conteo[paso["capa"]] - 1))
        alto_pila = {c: n * NODO_H + (n - 1) * 8 for c, n in conteo.items()}

        cajas = []
        for k, (paso, indice) in enumerate(posiciones):
            capa_id = paso["capa"]
            total = conteo[capa_id]
            x = COL_X0 + (capa_id - 1) * COL_W
            y = centro - alto_pila[capa_id] / 2 + indice * (NODO_H + 8)
            servicio = next(s for s in capas[capa_id]["servicios"] if s["id"] == paso["servicio"])
            lineas = _envolver(servicio["nombre"], FUENTE_NODO)[:2]
            piezas.append(f'      <g class="paso" style="--i:{k}">')
            piezas.append(f'        <rect class="nodo" x="{x:g}" y="{y:g}" width="{NODO_W}" height="{NODO_H}" rx="6"/>')
            base = y + NODO_H / 2 + (0 if len(lineas) == 1 else -4) + 4
            for i, linea in enumerate(lineas):
                piezas.append(_texto(x + NODO_W / 2, base + 12 * i, "s", _t(linea),
                                     ' text-anchor="middle"'))
            piezas.append("      </g>")
            cajas.append((x, y, total, paso))

        for i in range(len(cajas) - 1):
            x1, y1, _, _ = cajas[i]
            x2, y2, _, siguiente = cajas[i + 1]
            if abs(x1 - x2) < 0.5:                        # misma capa: bajan en vertical
                d = _ruta(x1 + NODO_W / 2, y1 + NODO_H, x2 + NODO_W / 2, y2)
            else:
                d = _ruta(x1 + NODO_W, y1 + NODO_H / 2, x2 - 2, y2 + NODO_H / 2)
            piezas.append(f'      <path class="ff" d="{d}"/>')
            via = siguiente.get("via")
            if via and abs(y1 - y2) < 0.5 and abs(x1 - x2) > 0.5:
                piezas.append(_texto((x1 + NODO_W + x2) / 2, y1 + NODO_H / 2 - 8, "m", _t(via),
                                     ' text-anchor="middle"'))
        piezas.append("    </g>")

    piezas.append(_texto(ANCHO - 30, alto_svg - 12, "m",
                         "Clic para aislar · Rueda: zoom · Arrastrá: mover · Esc: volver",
                         ' text-anchor="end"'))
    piezas.append("  </g>")
    return piezas, alto_svg


DEFS = """
    <marker id="{flecha}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
            markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--accent)"/>
    </marker>
    <marker id="{flecha_m}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
            markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 0 L 10 5 L 0 10 z" fill="var(--muted)"/>
    </marker>
    <pattern id="rejilla-{flecha}" width="28" height="28" patternUnits="userSpaceOnUse">
      <circle cx="1" cy="1" r="1" fill="var(--muted)" opacity=".16"/>
    </pattern>"""


def render_html(modelo: dict) -> str:
    piezas_capas, alto_capas = _svg_capas(modelo)
    piezas_flujo, alto_flujo = _svg_flujo(modelo)

    def envolver_svg(svg_id, piezas, alto, prefijo, etiqueta, oculto=False):
        return (f'<svg id="{svg_id}" class="vista" viewBox="0 0 {ANCHO} {alto:g}" '
                f'preserveAspectRatio="xMidYMin meet" '
                f'role="img" aria-label="{etiqueta}"'
                f'{" hidden=\"hidden\"" if oculto else ""}>\n  <defs>'
                + DEFS.format(flecha=f"flecha-{prefijo}", flecha_m=f"flecha-{prefijo}m")
                + "\n  </defs>\n"
                + f'<rect x="0" y="0" width="{ANCHO}" height="{alto:g}" '
                  f'fill="url(#rejilla-flecha-{prefijo})"/>\n'
                + "\n".join(piezas) + "\n</svg>")

    return (
        '<!DOCTYPE html>\n<html class="%%TEMA%%" lang="es">\n<head>\n'
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        "<title>Arquitectura de plataforma SMUCORP</title>\n<style>"
        f"{CSS}</style>\n</head>\n<body data-vista=\"capas\">\n"
        '<button id="volver" type="button" aria-label="Volver al esquema">← Volver</button>\n'
        '<header id="tabs" role="tablist">\n'
        '  <button class="tab" type="button" role="tab" data-vista="capas" aria-selected="true">Capas</button>\n'
        '  <button class="tab" type="button" role="tab" data-vista="flujo" aria-selected="false">Flujo</button>\n'
        "</header>\n"
        + envolver_svg("vista-capas", piezas_capas, alto_capas, "c",
                       "Esquema de arquitectura por capas")
        + "\n"
        + envolver_svg("vista-flujo", piezas_flujo, alto_flujo, "f",
                       "Flujos transaccionales por capas", oculto=True)
        + "\n\n<script>" + JS + "</script>\n</body>\n</html>\n"
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
