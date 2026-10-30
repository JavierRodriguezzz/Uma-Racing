"""Genera la documentación del proyecto (HTML + PDF) a partir del sistema real.

- Diccionario de datos y diagramas ER: se leen de database/schema.sql.
- Endpoints, métodos, códigos y roles: se leen de los routers de FastAPI.
- Historial de Git: se lee del repositorio.
- El PDF se imprime con Chrome headless (CDP) y el índice recibe los números de página en una segunda pasada.

Uso (desde la raíz del repo, con el entorno virtual del backend):
    backend/.venv/Scripts/python docs/documentacion/generar.py            # documento completo (16 secciones)
    backend/.venv/Scripts/python docs/documentacion/generar.py --avance   # entrega parcial: secciones 1–10 + anexos A–D
Requiere: Google Chrome, websockets (incluido en uvicorn[standard]) y pypdf (pip install pypdf).
"""
import asyncio
import base64
import html
import inspect
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

DOC = Path(__file__).resolve().parent
RAIZ = DOC.parents[1]
PLANTILLA = DOC / "plantilla.html"
SALIDA_HTML = DOC / "documentacion.html"
SALIDA_PDF = DOC / "UmaRacing_Documentacion.pdf"
CHROME = os.getenv("CHROME", r"C:\Program Files\Google\Chrome\Application\chrome.exe")
PUERTO = 9335

# Entrega parcial: el profesor pidió la documentación hasta "Diseño y documentación de API" (sección 10).
AVANCE = "--avance" in sys.argv
if AVANCE:
    SALIDA_HTML = DOC / "documentacion_avance.html"
    SALIDA_PDF = DOC / "UmaRacing_Documentacion_Avance.pdf"
AVANCE_VERSION = "0.3 (avance: secciones 1–10) — 30/10/2026"
AVANCE_FILA = ('<tr><td>0.3</td><td>30/10/2026</td><td>Javier A. Rodríguez Morales</td><td>Entrega de avance: '
               'secciones 1 a 10 (hasta Diseño y documentación de la API) y anexos A–D. Las secciones de módulos, seguridad, '
               'pruebas, instalación, resultados y la matriz de trazabilidad se entregan en la versión final.</td></tr>')
AVANCE_CAJA = ('<div class="caja"><b class="titulo">Alcance de esta entrega</b><p>Esta versión de avance comprende las '
               'secciones 1 a 10 de los lineamientos (hasta <i>Diseño y documentación de la API</i>) y los anexos técnicos '
               'que estas citan. Las referencias a las secciones 11 a 16 (módulos, seguridad, pruebas, instalación y control '
               'de versiones, resultados y trazabilidad) corresponden a la versión final del documento.</p></div>')

e = html.escape


def recortar_avance(texto):
    """Deja las secciones 1–10 y los anexos A–D; mueve a los anexos las figuras citadas que estaban en las secciones 11+."""
    i11 = texto.index("<!-- ============================================================ 11.")
    i16 = texto.index('<h2 id="s16">')
    i_e = texto.index('<h3 id="s16-e"')
    i_fin = texto.index('<script type="module">')
    quitado = texto[i11:i16]
    conservado = texto[:i11] + texto[i16:i_e]
    citadas = set(re.findall(r'data-fig="([\w-]+)"', conservado))
    figuras = [m.group(0) for m in re.finditer(r'<figure id="([\w-]+)".*?</figure>', quitado, re.S) if m.group(1) in citadas]
    extra = ""
    if figuras:
        figuras = [re.sub(r'\s*class="angosta"', "", f) for f in figuras]
        pares = ["\n".join(figuras[i:i + 2]) for i in range(0, len(figuras), 2)]
        extra = "\n".join(f'<div class="dos">\n{p}\n</div>' for p in pares)
    texto = conservado + extra + "\n\n" + texto[i_fin:]
    texto = texto.replace('<h2 id="s16">16. Anexos</h2>', '<h2 id="s16">11. Anexos</h2>')
    texto = re.sub(r"(<td>Versión del documento</td><td>)[^<]*", r"\g<1>" + AVANCE_VERSION, texto, count=1)
    texto = texto.replace("    <tr><td><span class=\"pendiente\">1.0</span>", "    " + AVANCE_FILA + "\n    <tr><td><span class=\"pendiente\">1.0</span>", 1)
    texto = texto.replace('<h3 class="h2-sin-salto" style="font-size:14pt;color:var(--azul);margin-top:22px">Índice</h3>',
                          AVANCE_CAJA + '\n<h3 class="h2-sin-salto" style="font-size:14pt;color:var(--azul);margin-top:22px">Índice</h3>', 1)
    return texto


# --------------------------------------------------------------------------- Esquema de BD
def _partir(cuerpo):
    """Divide las definiciones de CREATE TABLE por comas de primer nivel (ignora las de ENUM, DECIMAL, CHECK)."""
    partes, nivel, actual, comilla = [], 0, "", False
    for ch in cuerpo:
        if ch == "'":
            comilla = not comilla
        if not comilla:
            if ch == "(":
                nivel += 1
            elif ch == ")":
                nivel -= 1
            elif ch == "," and nivel == 0:
                partes.append(actual.strip())
                actual = ""
                continue
        actual += ch
    if actual.strip():
        partes.append(actual.strip())
    return partes


def leer_esquema():
    sql = (RAIZ / "database" / "schema.sql").read_text(encoding="utf-8")
    tablas = []
    patron = re.compile(r"--\s*(\d+)\.\s*([^\n]+)\n(?:--[^\n]*\n)*?(?:--\s*-+\n)CREATE TABLE (\w+) \((.*?)\n\) ENGINE", re.S)
    for num, titulo, nombre, cuerpo in patron.findall(sql):
        desc = re.search(r"\((.*)\)", titulo)
        t = {"num": int(num), "nombre": nombre, "titulo": titulo.strip(),
             "descripcion": desc.group(1) if desc else "", "columnas": [], "pk": [], "uq": [], "fk": [], "checks": [], "indices": []}
        for d in _partir(cuerpo.replace("\n", " ")):
            d = re.sub(r"\s+", " ", d)
            if d.startswith("PRIMARY KEY"):
                t["pk"] = re.findall(r"\w+", d[len("PRIMARY KEY"):])
            elif d.startswith("CONSTRAINT"):
                if " FOREIGN KEY " in d:
                    m = re.search(r"FOREIGN KEY \((\w+)\) REFERENCES (\w+) \((\w+)\)", d)
                    t["fk"].append(m.groups())
                elif " UNIQUE " in d:
                    t["uq"].append(re.search(r"UNIQUE \((.*?)\)", d).group(1).replace(" ", ""))
                elif " CHECK " in d:
                    t["checks"].append(d.split(" CHECK ", 1)[1])
            elif d.startswith("INDEX"):
                m = re.match(r"INDEX (\w+) \((.*?)\)", d)
                t["indices"].append((m.group(1), m.group(2).replace(" ", "")))
            else:
                m = re.match(r"(\w+)\s+(.*)", d)
                col, resto = m.groups()
                tipo = re.match(r"(ENUM\(.*?\)|\w+(?:\([\d, ]+\))?(?: UNSIGNED)?)", resto).group(1)
                defecto = re.search(r"DEFAULT ('[^']*'|[\w().]+(?: ON UPDATE \w+)?)", resto)
                t["columnas"].append({"nombre": col, "tipo": tipo, "nulo": "NOT NULL" not in resto,
                                      "defecto": defecto.group(1) if defecto else "",
                                      "auto": "AUTO_INCREMENT" in resto})
        tablas.append(t)
    return tablas


def _clave(t, col):
    claves = []
    if col in t["pk"]:
        claves.append("PK")
    if any(f[0] == col for f in t["fk"]):
        claves.append("FK")
    if any(col in u.split(",") for u in t["uq"]):
        claves.append("UQ")
    return ", ".join(claves)


def diccionario_html(tablas):
    bloques = []
    for t in tablas:
        filas = []
        for c in t["columnas"]:
            ref = next((f"→ {f[1]}.{f[2]}" for f in t["fk"] if f[0] == c["nombre"]), "")
            extra = " ".join(x for x in ["AUTO_INCREMENT" if c["auto"] else "", f"DEFAULT {c['defecto']}" if c["defecto"] else "", ref] if x)
            filas.append(f"<tr><td><code>{e(c['nombre'])}</code></td><td><code>{e(c['tipo'])}</code></td>"
                         f"<td>{'Sí' if c['nulo'] else 'No'}</td><td>{_clave(t, c['nombre'])}</td><td>{e(extra)}</td></tr>")
        notas = []
        if t["checks"]:
            notas.append("<b>CHECK:</b> " + "; ".join(f"<code>{e(c)}</code>" for c in t["checks"]))
        if t["indices"]:
            notas.append("<b>Índices:</b> " + ", ".join(f"<code>{e(n)}({e(c)})</code>" for n, c in t["indices"]))
        bloques.append(f"""
<div class="dic-tabla">
  <h4>{t['num']}. <code>{t['nombre']}</code> — {e(t['titulo'].split('(')[0].strip().capitalize())}</h4>
  {f'<p class="nota">{e(t["descripcion"].capitalize())}.</p>' if t['descripcion'] else ''}
  <table class="tabla compacta"><thead><tr><th>Campo</th><th>Tipo</th><th>Nulo</th><th>Clave</th><th>Default / referencia</th></tr></thead>
  <tbody>{''.join(filas)}</tbody></table>
  {''.join(f'<p class="nota">{n}</p>' for n in notas)}
</div>""")
    return "\n".join(bloques)


def _tipo_mermaid(tipo):
    return re.match(r"\w+", tipo).group(0).lower()


def mermaid_er(tablas, incluir, con_atributos=True, direccion=None):
    por_nombre = {t["nombre"]: t for t in tablas}
    lineas = (['%%{init: {"themeVariables": {"fontSize": "24px"}, "er": {"minEntityWidth": 230}}}%%'] if not con_atributos else []) + ["erDiagram"] + ([f"  direction {direccion}"] if direccion else [])
    vistos = set()
    for nombre in incluir:
        t = por_nombre[nombre]
        if con_atributos:
            lineas.append(f"  {nombre} {{")
            for c in t["columnas"]:
                k = _clave(t, c["nombre"]).replace(" ", "")
                lineas.append(f"    {_tipo_mermaid(c['tipo'])} {c['nombre']}{(' ' + k.replace('UQ', 'UK')) if k else ''}")
            lineas.append("  }")
        for col, ref, _ in t["fk"]:
            if ref not in incluir and not con_atributos:
                continue
            c = next(x for x in t["columnas"] if x["nombre"] == col)
            uno_a_uno = t["pk"] == [col]
            izq = "|o" if c["nulo"] else "||"
            der = "o|" if uno_a_uno else "o{"
            clave = (ref, nombre, col)
            if clave not in vistos:
                vistos.add(clave)
                lineas.append(f'  {ref} {izq}--{der} {nombre} : "{col}"')
    return "\n".join(lineas)


# --------------------------------------------------------------------------- API
def leer_endpoints():
    sys.path.insert(0, str(RAIZ / "backend"))
    from fastapi.routing import APIRoute  # noqa: E402
    from app.routers import (anuncios, apuestas, auth, compras, dormitorio, gacha, items, logros, monedas,  # noqa: E402
                             panel, partidas, perfil, ranking, tiempo, usuarios)

    def roles(dep, acc):
        nombre = getattr(dep.call, "__name__", "")
        if nombre == "_verificar":
            acc.add(dep.call.__closure__[0].cell_contents[0])
        elif nombre == "usuario_actual":
            acc.add("autenticado")
        for d in dep.dependencies:
            roles(d, acc)
        return acc

    modulos = [("Autenticación", auth), ("Perfil", perfil), ("Tienda — artículos", items), ("Tienda — compras", compras),
               ("Publicidad", anuncios), ("Partidas", partidas), ("Ranking", ranking), ("Logros", logros),
               ("Usuarios (admin)", usuarios), ("Dashboard, reportes y bitácora", panel), ("Monedas y Google Pay", monedas),
               ("Tiempo de juego", tiempo), ("Apuestas", apuestas), ("Gachapón", gacha), ("Dormitorio", dormitorio)]
    salida = []
    orden_metodo = {"GET": 0, "POST": 1, "PUT": 2, "PATCH": 3, "DELETE": 4}
    for titulo, m in modulos:
        rutas = []
        for r in m.router.routes:
            if not isinstance(r, APIRoute):
                continue
            rs = roles(r.dependant, set())
            if "administrador" in rs:
                rol = "Administrador"
            elif "jugador" in rs:
                rol = "Jugador"
            elif rs and re.search(r"es_admin\(usuario\)[^\n]*\n\s*raise APIError\(403", inspect.getsource(r.endpoint)):
                rol = "Jugador*"  # el endpoint rechaza al administrador dentro de su lógica
            elif rs:
                rol = "Autenticado"
            else:
                rol = "Público"
            cuerpo = getattr(r.body_field.field_info.annotation, "__name__", "") if r.body_field is not None else ""
            params = [p.name for p in r.dependant.query_params]
            for met in sorted(r.methods, key=orden_metodo.get):
                rutas.append({"metodo": met, "ruta": r.path, "resumen": r.summary or "", "rol": rol,
                              "codigo": r.status_code or 200, "cuerpo": cuerpo, "query": params})
        salida.append((titulo, rutas))
    return salida


def endpoints_html(modulos):
    bloques = []
    total = 0
    for titulo, rutas in modulos:
        filas = []
        for r in rutas:
            total += 1
            entrada = []
            if r["cuerpo"]:
                entrada.append(f"JSON <code>{e(r['cuerpo'])}</code>")
            if r["query"]:
                entrada.append("Query: " + ", ".join(f"<code>{e(q)}</code>" for q in r["query"]))
            filas.append(f"<tr><td><span class='met met-{r['metodo'].lower()}'>{r['metodo']}</span></td>"
                         f"<td><code>{e(r['ruta'])}</code></td><td>{e(r['resumen'])}</td>"
                         f"<td>{'<br>'.join(entrada) or '—'}</td><td>{r['codigo']}</td><td>{r['rol']}</td></tr>")
        bloques.append(f"<h4>{e(titulo)}</h4><table class='tabla compacta endpoints'><thead><tr><th>Método</th><th>Endpoint</th>"
                       f"<th>Función</th><th>Entrada</th><th>Éxito</th><th>Rol</th></tr></thead><tbody>{''.join(filas)}</tbody></table>")
    return "\n".join(bloques), total


# --------------------------------------------------------------------------- Git
def git_log():
    salida = subprocess.run(["git", "-C", str(RAIZ), "log", "--reverse", "--date=format:%d/%m/%Y %H:%M",
                             "--format=%h|%ad|%an|%s"], capture_output=True, text=True, encoding="utf-8").stdout
    filas = []
    for linea in salida.strip().splitlines():
        h, fecha, autor, msg = linea.split("|", 3)
        filas.append(f"<tr><td><code>{h}</code></td><td>{fecha}</td><td>{e(autor)}</td><td>{e(msg)}</td></tr>")
    return "\n".join(filas), len(filas)


# --------------------------------------------------------------------------- Ensamblado
GRUPOS_ER = {
    "ER_USUARIOS": ["roles", "usuarios", "sesiones", "perfiles", "logros", "usuario_logros", "bitacora"],
    "ER_TIENDA": ["tipos_item", "items", "compras", "inventario_usuario", "movimientos_monedas", "anuncios",
                  "visualizaciones_anuncio", "paquetes_monedas", "ordenes_pago"],
    "ER_JUEGO": ["partidas", "sesiones_juego", "atributos_carrera", "apuestas", "gacha_premios", "gacha_tiradas",
                 "gacha_resultados"],
    "ER_DORMITORIO": ["dormitorios", "dormitorio_muebles", "atributos_mueble"],
}


def construir_html(paginas_toc=None):
    tablas = leer_esquema()
    assert len(tablas) == 26, f"Se esperaban 26 tablas y se leyeron {len(tablas)}"
    texto = PLANTILLA.read_text(encoding="utf-8")
    if AVANCE:
        texto = recortar_avance(texto)
    reemplazos = {"DICCIONARIO": diccionario_html(tablas),
                  "ER_COMPLETO": mermaid_er(tablas, [t["nombre"] for t in tablas], con_atributos=False, direccion="LR")}
    for clave, grupo in GRUPOS_ER.items():
        reemplazos[clave] = mermaid_er(tablas, grupo)
    endpoints, total = endpoints_html(leer_endpoints())
    reemplazos["ENDPOINTS"] = endpoints
    reemplazos["TOTAL_ENDPOINTS"] = str(total + 1)  # + /api/salud
    reemplazos["GIT_LOG"], reemplazos["TOTAL_COMMITS"] = git_log()
    reemplazos["TOTAL_COMMITS"] = str(reemplazos["TOTAL_COMMITS"])
    pruebas = DOC / "resultado_pruebas.txt"
    reemplazos["PRUEBAS"] = e(pruebas.read_text(encoding="utf-8")) if pruebas.exists() else "(ejecuta pytest -v y guarda la salida en resultado_pruebas.txt)"
    for clave, valor in reemplazos.items():
        texto = texto.replace("{{" + clave + "}}", valor)

    # Índice: se arma con los h2/h3 numerados (data-toc) del documento
    entradas = re.findall(r'<h([23]) id="([\w-]+)"[^>]*>(.*?)</h\1>', texto)
    lineas = []
    for nivel, ident, titulo in entradas:
        limpio = re.sub(r"<[^>]+>", "", titulo).strip()
        pagina = (paginas_toc or {}).get(ident, "00")
        lineas.append(f'<li class="toc-{nivel}"><a href="#{ident}"><span>{limpio}</span><span class="toc-pag">{pagina}</span></a></li>')
    texto = texto.replace("{{INDICE}}", "\n".join(lineas))
    # Marca invisible en cada título para localizar su página en el PDF
    texto = re.sub(r'<h([23]) id="([\w-]+)"([^>]*)>', lambda m: f'<h{m.group(1)} id="{m.group(2)}"{m.group(3)}><span class="marca">QQ{m.group(2).replace("-", "")}QQ</span>', texto)
    SALIDA_HTML.write_text(texto, encoding="utf-8")
    return [ident for _, ident, _ in entradas]


async def imprimir_pdf():
    import websockets
    perfil = tempfile.mkdtemp(prefix="uma-pdf-")
    proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PUERTO}", f"--user-data-dir={perfil}",
                             "--no-first-run", "about:blank"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        for _ in range(60):
            try:
                tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json"))
                break
            except Exception:
                time.sleep(0.25)
        ws_url = next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page")
        async with websockets.connect(ws_url, max_size=500_000_000) as ws:
            n = 0
            pend = {}

            async def cmd(metodo, **params):
                nonlocal n
                n += 1
                fut = asyncio.get_event_loop().create_future()
                pend[n] = fut
                await ws.send(json.dumps({"id": n, "method": metodo, "params": params}))
                return await fut

            async def lector():
                async for m in ws:
                    d = json.loads(m)
                    if d.get("id") in pend:
                        pend.pop(d["id"]).set_result(d.get("result", d.get("error")))

            asyncio.create_task(lector())
            await cmd("Page.enable")
            await cmd("Page.navigate", url=SALIDA_HTML.as_uri())
            for _ in range(120):  # espera fuentes, imágenes y diagramas Mermaid
                r = await cmd("Runtime.evaluate", expression="window.__listo === true")
                if r.get("result", {}).get("value"):
                    break
                await asyncio.sleep(0.5)
            else:
                raise RuntimeError("Los diagramas no terminaron de renderizarse.")
            r = await cmd("Page.printToPDF", printBackground=True, preferCSSPageSize=True, generateDocumentOutline=True,
                          generateTaggedPDF=True)
            SALIDA_PDF.write_bytes(base64.b64decode(r["data"]))
    finally:
        proc.kill()


def paginas_de_titulos(ids):
    from pypdf import PdfReader
    lector = PdfReader(str(SALIDA_PDF))
    paginas = {}
    for i, pag in enumerate(lector.pages, start=1):
        texto = (pag.extract_text() or "").replace(" ", "").replace("\n", "")
        for ident in ids:
            if ident not in paginas and f"QQ{ident.replace('-', '')}QQ" in texto:
                paginas[ident] = str(i)
    faltan = [i for i in ids if i not in paginas]
    if faltan:
        print("Aviso: no se encontró la página de", faltan)
    return paginas, len(lector.pages)


if __name__ == "__main__":
    ids = construir_html()
    asyncio.run(imprimir_pdf())
    paginas, _ = paginas_de_titulos(ids)
    construir_html(paginas)
    asyncio.run(imprimir_pdf())
    paginas2, total = paginas_de_titulos(ids)
    if paginas2 != paginas:
        print("Aviso: la paginación cambió entre pasadas; revisa el índice.")
    print(f"Listo: {SALIDA_PDF} ({total} páginas)")
