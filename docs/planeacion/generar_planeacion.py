"""Genera Planeacion_Proyecto_Equipo01.pdf (plan de trabajo del proyecto final).

Las actividades se definen UNA vez en ACTIVIDADES; de ahí salen la tabla de actividades, el cronograma,
la carga por integrante y los diagramas de Gantt. Reutiliza la impresión a PDF de docs/documentacion/generar.py.

Uso (desde la raíz del repo):  backend/.venv/Scripts/python docs/planeacion/generar_planeacion.py
"""
import asyncio
import html
import re
import sys
from datetime import date, timedelta
from pathlib import Path

DOC = Path(__file__).resolve().parent
sys.path.insert(0, str(DOC.parent / "documentacion"))
import generar as base  # noqa: E402

PLANTILLA = DOC / "plantilla_planeacion.html"
SALIDA_HTML = DOC / "planeacion.html"
SALIDA_PDF = DOC / "Planeacion_Proyecto_Equipo01.pdf"
ANIO = 2026
e = html.escape

PERSONAS = {
    "JR": ("Javier Antonio Rodríguez Morales", "Javier R.", "#0d97ba"),
    "MM": ("Marco Antonio Muñoz Malpica", "Marco M.", "#e2438f"),
    "JG": ("José Oliver Guzmán Camacho", "José G.", "#b98300"),
    "EQ": ("Todo el equipo", "Equipo", "#6b7280"),
}

FASES = {
    "F0": "Planeación y análisis", "F1": "Diseño", "F2": "Base de datos", "F3": "Backend y API",
    "F4": "Frontend", "F5": "Integración", "F6": "Pruebas", "F7": "Correcciones", "F8": "Despliegue",
    "F9": "Documentación", "F10": "Entrega",
}

# (id, fase, corto, descripción, responsable, apoyo, inicio, fin, horas, dependencias, entregable, criterio de terminado)
ACTIVIDADES = [
    ("A01", "F0", "Requisitos obligatorios", "Revisar lineamientos y requerimientos y elaborar la lista de requisitos obligatorios", "JR", "MM, JG", "07/10", "08/10", 4, "—", "Matriz de requisitos (sección 2)", "Cada requisito obligatorio tiene módulo, actividad y responsable."),
    ("A02", "F0", "Repositorio y tablero", "Configurar el repositorio (ramas main, develop y feature/*, .gitignore, .env.example) y el tablero de tareas", "JR", "—", "08/10", "08/10", 2, "—", "Repositorio en GitHub y tablero GitHub Projects", "Los 3 integrantes tienen acceso y un commit propio en develop."),
    ("A03", "F0", "RF y RNF", "Definir requerimientos funcionales y no funcionales numerados (RF-xx, RNF-xx)", "MM", "JR, JG", "08/10", "09/10", 5, "A01", "docs/requerimientos.md", "RF y RNF numerados y revisados por los tres integrantes."),
    ("A04", "F0", "Reglas y criterios", "Definir al menos 5 reglas de negocio y los criterios de aceptación de cada módulo", "JG", "JR, MM", "08/10", "09/10", 4, "A01", "docs/requerimientos.md", "Al menos 5 RN verificables; cada módulo con condiciones observables."),
    ("A05", "F0", "Modelo de negocio", "Describir el modelo de negocio y el contexto de uso", "JG", "—", "09/10", "09/10", 3, "A01", "Borrador de la sección 4 del PDF", "Incluye los 9 elementos mínimos del lineamiento 7.1."),
    ("A06", "F0", "Plan de trabajo", "Elaborar este plan: actividades, cronograma, Gantt, riesgos y plan de pruebas", "JG", "JR, MM", "07/10", "09/10", 6, "A01", "Planeacion_Proyecto_Equipo01.pdf", "Entregado en Teams (Proyecto Unidad 2)."),
    ("A07", "F1", "Arquitectura", "Diagrama de arquitectura cliente-servidor y estructura de carpetas", "JR", "—", "10/10", "11/10", 3, "A03", "docs/diagrams/arquitectura", "Muestra usuario, frontend, API, backend, BD y servicios externos."),
    ("A08", "F1", "Wireframes", "Wireframes de login, dashboard, tienda, formulario, detalle y reportes", "MM", "JG", "10/10", "12/10", 6, "A03", "docs/diagrams/wireframes", "Las 6 pantallas mínimas del lineamiento 11.1."),
    ("A09", "F1", "Modelo ER y diccionario", "Modelo entidad-relación en 3FN y diccionario de datos", "JR", "MM, JG", "11/10", "13/10", 6, "A03, A04", "docs/database.md y diagrama ER", "Al menos 6 tablas relacionadas, con PK, FK y cardinalidades; 3FN justificada."),
    ("A10", "F1", "Diseño de la API", "Lista de endpoints con método, entrada, respuesta, códigos HTTP y rol", "JR", "MM, JG", "12/10", "14/10", 5, "A09", "docs/api.md (borrador)", "Al menos 12 endpoints con permiso por rol."),
    ("A11", "F1", "Guía visual", "Paleta, tipografía, componentes y estados de interfaz", "MM", "—", "12/10", "14/10", 4, "A08", "docs/ux.md", "Contraste validado; estados de carga, vacío, error y éxito definidos."),
    ("A12", "F2", "Tablas núcleo", "schema.sql: roles, usuarios, sesiones, perfiles y catálogo de artículos", "JR", "—", "13/10", "14/10", 5, "A09", "database/schema.sql", "La BD se crea desde cero sin errores en MariaDB."),
    ("A13", "F2", "Tablas de tienda", "Tablas de compras, inventario, movimientos de monedas, paquetes y órdenes de pago", "JR", "—", "14/10", "15/10", 4, "A12", "database/schema.sql", "FK, UNIQUE y CHECK de saldo definidos."),
    ("A14", "F2", "Tablas de juego", "Tablas de partidas, logros, sesiones de juego, apuestas y atributos de carrera", "MM", "—", "14/10", "15/10", 4, "A12", "database/schema.sql", "FK e índices por usuario y fecha definidos."),
    ("A15", "F2", "Tablas de publicidad", "Tablas de anuncios, visualizaciones, gachapón y bitácora", "JG", "—", "14/10", "15/10", 4, "A12", "database/schema.sql", "FK y CHECK de probabilidades y duraciones definidos."),
    ("A16", "F2", "Datos semilla", "Datos semilla y de demostración (seed.sql, seed_demo.sql) y script de reinicio", "JG", "JR", "15/10", "16/10", 5, "A13, A14, A15", "database/seed.sql, seed_demo.sql", "Se cargan sin errores; hay cuentas de prueba para cada rol."),
    ("A17", "F3", "Núcleo de la API", "Configuración por .env, consultas parametrizadas, transacciones y manejo uniforme de errores", "JR", "—", "15/10", "16/10", 8, "A12", "backend/app (núcleo)", "/api/salud responde; los errores son JSON sin SQL ni trazas."),
    ("A18", "F3", "Autenticación y roles", "Registro, login, logout con revocación, bcrypt, JWT y permisos por rol", "JR", "—", "16/10", "19/10", 10, "A17", "/api/auth/*, security.py", "Sin token responde 401; con rol incorrecto, 403; contraseñas con hash."),
    ("A19", "F3", "Listados", "Búsqueda, filtros, ordenamiento con lista blanca y paginación estándar", "JG", "—", "16/10", "18/10", 5, "A17", "services/consultas.py", "Respuesta {pagina, limite, total, totalPaginas, datos}."),
    ("A20", "F3", "API de tienda", "CRUD de artículos, compra transaccional con folio, inventario, libro mayor y reembolso", "JR", "MM", "19/10", "22/10", 16, "A13, A18, A19", "/api/items, /api/compras", "Compra con COMMIT y ROLLBACK comprobados."),
    ("A21", "F3", "API de partidas", "Registro de partidas, validación antitrampa, puntaje, monedas, logros automáticos y ranking", "MM", "JR", "19/10", "22/10", 16, "A14, A18", "/api/partidas, /api/logros, /api/ranking", "Un resultado imposible se rechaza; los logros se otorgan solos."),
    ("A22", "F3", "API de publicidad", "Publicidad simulada con recompensa validada por el servidor y CRUD de anuncios", "JG", "—", "19/10", "20/10", 8, "A15, A18", "/api/anuncios", "No paga si el anuncio no se vio completo; límite diario."),
    ("A23", "F3", "API de usuarios y bitácora", "CRUD de usuarios (baja lógica, ajuste de monedas) y bitácora de operaciones", "JG", "JR", "20/10", "22/10", 10, "A18, A19", "/api/usuarios, /api/bitacora", "Operaciones críticas registradas con estado anterior y nuevo."),
    ("A24", "F3", "API de Google Pay", "Paquetes de monedas y compra con Google Pay en modo TEST", "JR", "—", "24/10", "27/10", 10, "A20", "/api/paquetes, /api/pagos", "La orden se paga una sola vez y vence en 15 minutos."),
    ("A25", "F3", "API de tiempo y apuestas", "Monedas por tiempo de juego activo y apuestas (carrera simulada y reto de tiempo)", "MM", "—", "24/10", "28/10", 14, "A20, A21", "/api/tiempo-juego, /api/apuestas", "Límites de juego responsable; el resultado lo decide el servidor."),
    ("A26", "F3", "API de gachapón", "Gachapón con probabilidades públicas y CRUD de premios", "JG", "—", "24/10", "26/10", 10, "A20", "/api/gacha", "Las probabilidades suman 100 %; garantía de premio épico."),
    ("A27", "F3", "API de dashboard y reportes", "Dashboard por rol y 4 reportes con rango de fechas", "JG", "JR, MM", "26/10", "29/10", 12, "A20, A21, A22, A23", "/api/dashboard, /api/reportes/*", "Datos tomados de la BD; un rango de fechas inválido responde 422."),
    ("A28", "F4", "Juego en el navegador", "Compilar el juego a WebAssembly con pygbag y una plantilla propia", "MM", "—", "13/10", "15/10", 6, "—", "game/build/web, plantilla_juego/", "El juego carga en el navegador sin cambiar su jugabilidad."),
    ("A29", "F4", "Base del frontend", "Layout y menú por rol, cliente de API, tabla y CRUD reutilizables, estados, confirmaciones y diseño responsivo", "MM", "JG", "15/10", "19/10", 14, "A10, A11", "frontend/js, frontend/css", "Navegación coherente a 1366, 820 y 390 px."),
    ("A30", "F4", "Login, registro y perfil", "Pantallas de login, registro y perfil", "JR", "MM", "20/10", "21/10", 6, "A18, A29", "login.html, registro.html, perfil.html", "Validación en el frontend y mensajes del servidor visibles."),
    ("A31", "F4", "Pantallas de tienda", "Pantallas de tienda e historial de compras y movimientos", "JR", "—", "22/10", "23/10", 8, "A20, A29", "tienda.html, historial", "Compra con confirmación y saldo actualizado sin recargar."),
    ("A32", "F4", "Pantallas de juego", "Pantallas de jugar, historial de partidas, ranking y logros", "MM", "—", "21/10", "22/10", 10, "A21, A29", "jugar.html, ranking.html, logros.html", "Datos de la API con filtros y paginación."),
    ("A33", "F4", "Pantallas de administración", "Pantallas de anuncios, administración (usuarios, artículos, anuncios, logros) y bitácora", "JG", "MM", "21/10", "23/10", 12, "A22, A23, A29", "anuncios.html, admin/*.html", "CRUD completo con confirmaciones; un jugador no puede acceder."),
    ("A34", "F4", "Pantalla de monedas", "Compra de monedas con Google Pay y administración de paquetes", "JR", "—", "27/10", "28/10", 6, "A24", "monedas.html, admin/paquetes.html", "Pago de prueba acreditado y visible en el historial."),
    ("A35", "F4", "Pantalla de apuestas", "Apuestas con carrera animada y tiempo de juego en jugar.html", "MM", "—", "28/10", "29/10", 8, "A25", "apuestas.html", "La animación repite la carrera decidida por el servidor."),
    ("A36", "F4", "Pantalla de gachapón", "Pantalla del gachapón y administración de premios", "JG", "—", "26/10", "27/10", 6, "A26", "gacha.html, admin/gacha.html", "Muestra probabilidades públicas y contador de garantía."),
    ("A37", "F4", "Dashboard y reportes", "Dashboard y reportes con Chart.js, filtro de fechas y exportación CSV", "JG", "MM", "29/10", "30/10", 8, "A27, A29", "dashboard.html, admin/reportes.html", "Al menos 2 gráficas dinámicas con datos de la API."),
    ("A38", "F5", "Integración juego–API", "Candados según inventario, registro de partidas y latidos de tiempo de juego", "MM", "JR", "22/10", "23/10", 8, "A21, A28, A32", "game/conexion.py, jugar.html", "Una partida jugada en el navegador queda registrada en la BD."),
    ("A39", "F5", "Integración en develop", "Integrar ramas en develop con revisión cruzada (pull requests) y prueba de humo", "JR", "MM, JG", "29/10", "30/10", 6, "A30–A38", "develop estable (congelamiento de funciones)", "El flujo punta a punta funciona sin errores."),
    ("A40", "F6", "Pruebas automatizadas", "Pruebas de API con pytest y BD aislada: cada integrante cubre sus módulos; José G. coordina la suite", "EQ", "—", "21/10", "31/10", 16, "A20–A27", "backend/tests", "Cubren éxito, datos inválidos, permisos, inexistente, duplicado, regla crítica y transacción."),
    ("A41", "F6", "Pruebas manuales", "Pruebas de diseño responsivo, estados de interfaz, error de conexión y flujo punta a punta con capturas", "MM", "JG", "31/10", "01/11", 6, "A39", "Capturas en docs/", "Cada caso manual con evidencia de captura."),
    ("A42", "F6", "Matriz de pruebas", "Matriz de pruebas y registro de defectos", "JG", "—", "01/11", "02/11", 4, "A40, A41", "docs/pruebas.md", "Cada caso tiene su resultado obtenido y su estado."),
    ("A43", "F7", "Corrección de defectos", "Corregir defectos y volver a ejecutar las pruebas", "EQ", "—", "02/11", "04/11", 12, "A42", "Commits fix: en develop", "Ningún defecto crítico abierto; la suite completa aprueba."),
    ("A44", "F8", "Despliegue", "Dockerfiles y docker-compose (db, api, nginx) y despliegue en Portainer desde GitHub", "JG", "JR", "28/10", "02/11", 10, "A27", "Dockerfile, docker-compose.yml", "Sistema accesible en una URL pública."),
    ("A45", "F9", "Documentación semanal", "Cada viernes, cada responsable actualiza la documentación de sus módulos y registra los cambios al cronograma", "EQ", "—", "09/10", "30/10", 8, "—", "docs/ actualizado", "Un commit docs: por integrante cada semana."),
    ("A46", "F9", "README", "README con instalación, configuración, variables de entorno, usuarios de prueba y endpoints", "JR", "JG", "20/10", "03/11", 4, "A18", "README.md", "Una persona ajena instala y ejecuta el sistema siguiéndolo."),
    ("A47", "F9", "Documentación de API", "Swagger/OpenAPI y docs/api.md con parámetros, cuerpos, respuestas, códigos y permisos", "JR", "MM, JG", "27/10", "03/11", 5, "A20–A27", "/docs y docs/api.md", "Todos los endpoints documentados con su rol."),
    ("A48", "F9", "Redacción del PDF", "Redactar el PDF final por secciones: Javier (7, 9, 10, 12), Marco (3, 4, 8, 11), José (2, 5, 13, 14, 15, 16)", "EQ", "—", "30/10", "04/11", 15, "A39", "Borrador del PDF final", "Las 16 secciones obligatorias redactadas."),
    ("A49", "F9", "Revisión del PDF", "Ensamblar, revisar en cruzado y aplicar el checklist del PDF final", "JG", "JR, MM", "04/11", "05/11", 4, "A48", "UmaRacing_Documentacion.pdf", "Checklist de los lineamientos completo."),
    ("A50", "F10", "Ensayo de demo", "Ensayar la demostración: guion, cuentas y datos de prueba", "EQ", "—", "05/11", "05/11", 3, "A43, A44", "Guion de la demostración", "La demo se completa en el tiempo asignado."),
    ("A51", "F10", "Entrega final", "Etiqueta v1.0.0, push a GitHub, entrega del PDF y demostración", "JG", "JR, MM", "06/11", "06/11", 2, "A49, A50", "Release v1.0.0 y PDF en Teams", "Entregado en la fecha indicada por el docente."),
]

FASE_INFO = {
    "F0": ("Matriz de requisitos, RF/RNF, reglas de negocio, modelo de negocio y plan de trabajo", "docs/requerimientos.md y Planeacion_Proyecto_Equipo01.pdf en Teams"),
    "F1": ("Arquitectura, wireframes, modelo ER, diccionario de datos, diseño de API y guía visual", "docs/diagrams/, docs/database.md, docs/api.md y docs/ux.md en el repositorio"),
    "F2": ("Script de creación de la BD (al menos 6 tablas en 3FN) y datos semilla", "schema.sql y seed.sql ejecutados sin errores en MariaDB"),
    "F3": ("API REST con autenticación, roles, reglas de negocio, transacciones y reportes", "Endpoints visibles en Swagger (/docs) y pruebas de cada módulo aprobadas"),
    "F4": ("Juego en el navegador y pantallas del jugador y del administrador", "Pantallas funcionando contra la API; capturas en docs/"),
    "F5": ("Juego conectado con la API y ramas integradas en develop", "Partida jugada en el navegador registrada en la BD; develop estable"),
    "F6": ("Suite automatizada, pruebas manuales y matriz de pruebas", "backend/tests aprobado; docs/pruebas.md con resultados"),
    "F7": ("Defectos corregidos", "Commits fix: en develop y suite completa aprobada"),
    "F8": ("Sistema desplegado con Docker y Portainer", "URL pública funcionando"),
    "F9": ("README, documentación de API y PDF final actualizados", "README.md, /docs, docs/api.md y PDF con el checklist completo"),
    "F10": ("Versión v1.0.0, PDF y demostración", "Release en GitHub y entrega en Teams"),
}

HITOS = [
    ("H1", "09/10", "Plan de trabajo entregado; requisitos, reglas y modelo de negocio definidos"),
    ("H2", "16/10", "BD creada con datos semilla, núcleo de la API y juego en el navegador"),
    ("H3", "23/10", "MVP: autenticación, tienda, partidas, publicidad y administración integradas"),
    ("H4", "30/10", "Congelamiento de funciones: todos los módulos integrados en develop"),
    ("H5", "04/11", "Defectos críticos corregidos, sistema desplegado y PDF en revisión"),
    ("H6", "06/11", "Entrega final: sistema, repositorio, PDF y demostración"),
]


def f(dm):
    d, m = map(int, dm.split("/"))
    return date(ANIO, m, d)


def fmt(dm):
    return f(dm).strftime("%d/%m/%Y")


def nombre(cod):
    return PERSONAS[cod][1]


def apoyo(txt):
    return ", ".join(PERSONAS[c.strip()][1] for c in txt.split(",")) if txt != "—" else "—"


def validar():
    ids = {a[0] for a in ACTIVIDADES}
    fin = {a[0]: f(a[7]) for a in ACTIVIDADES}
    for a in ACTIVIDADES:
        assert f(a[6]) <= f(a[7]), a[0]
        assert f(a[7]) <= date(ANIO, 11, 6), a[0]
        for dep in re.findall(r"A\d\d(?:–A\d\d)?", a[9]):
            rango = dep.split("–")
            for r in rango:
                assert r in ids, (a[0], r)


# --------------------------------------------------------------------------- tablas
def tabla_actividades():
    filas = []
    for fase, titulo in FASES.items():
        filas.append(f'<tr class="fase"><td colspan="7">{fase.replace("F", "Fase ")} · {titulo}</td></tr>')
        for a in [x for x in ACTIVIDADES if x[1] == fase]:
            dias = (f(a[7]) - f(a[6])).days + 1
            ap = f"<br><span class='nota'>Apoyo: {apoyo(a[5])}</span>" if a[5] != "—" else ""
            filas.append(f"<tr><td><b>{a[0]}</b></td><td>{e(a[3])}</td><td><b>{nombre(a[4])}</b>{ap}</td>"
                         f"<td>{a[8]} h<br><span class='nota'>{dias} día{'s' if dias > 1 else ''}</span></td><td>{e(a[9])}</td>"
                         f"<td>{e(a[10])}</td><td>{e(a[11])}</td></tr>")
    return "\n".join(filas)


def tabla_cronograma():
    filas = []
    for fase, titulo in FASES.items():
        acts = [x for x in ACTIVIDADES if x[1] == fase]
        ini = min(f(a[6]) for a in acts)
        fin = max(f(a[7]) for a in acts)
        resp = sorted({a[4] for a in acts}, key=list(PERSONAS).index)
        entreg, crit = FASE_INFO[fase]
        filas.append(f"<tr><td><b>{titulo}</b><br><span class='nota'>{acts[0][0]}–{acts[-1][0]}</span></td><td>{ini:%d/%m/%Y}</td><td>{fin:%d/%m/%Y}</td>"
                     f"<td>{', '.join(nombre(r) for r in resp)}</td><td>{e(entreg)}</td><td>{e(crit)}</td><td>Planeado</td></tr>")
    return "\n".join(filas)


def tabla_hitos():
    return "\n".join(f"<tr><td><b>{h}</b></td><td>{fmt(d)}</td><td>{f(d):%A}</td><td>{e(t)}</td><td>Planeado</td></tr>"
                     .replace("Monday", "lunes").replace("Tuesday", "martes").replace("Wednesday", "miércoles")
                     .replace("Thursday", "jueves").replace("Friday", "viernes").replace("Saturday", "sábado").replace("Sunday", "domingo")
                     for h, d, t in HITOS)


def tabla_carga():
    horas = {k: 0.0 for k in PERSONAS if k != "EQ"}
    num = {k: 0 for k in horas}
    apoyo_n = {k: 0 for k in horas}
    for a in ACTIVIDADES:
        if a[4] == "EQ":
            for k in horas:
                horas[k] += a[8] / 3
        else:
            horas[a[4]] += a[8]
            num[a[4]] += 1
        for c in a[5].split(","):
            if c.strip() in apoyo_n:
                apoyo_n[c.strip()] += 1
    total = sum(horas.values())
    modulos = {
        "JR": "Núcleo (BD, API, autenticación), tienda y monedero, Google Pay, README y documentación de API",
        "MM": "Juego en el navegador, partidas, logros, ranking, tiempo de juego, apuestas, base del frontend y UX/UI",
        "JG": "Publicidad, gachapón, usuarios y bitácora, búsqueda y paginación, dashboard y reportes, pruebas, despliegue y ensamble del PDF",
    }
    filas = "\n".join(f"<tr><td><b>{PERSONAS[k][0]}</b></td><td>{modulos[k]}</td><td>{num[k]}</td><td>{apoyo_n[k]}</td>"
                      f"<td>{horas[k]:.0f} h</td><td>{horas[k] / total * 100:.0f} %</td></tr>" for k in horas)
    return filas + f"<tr><td colspan='4'><b>Total estimado</b></td><td><b>{total:.0f} h</b></td><td>100 %</td></tr>"


# --------------------------------------------------------------------------- Gantt
def gantt(filas, ini, fin, ancho=1000, etiqueta=290, alto_fila=17, hitos=()):
    """filas: [(texto, inicio, fin, color, es_fase)]  -> SVG"""
    dias = (fin - ini).days + 1
    x0 = etiqueta
    dx = (ancho - x0 - 8) / dias
    top = 48
    alto = top + alto_fila * len(filas) + 8
    o = [f'<svg viewBox="0 0 {ancho} {alto}" xmlns="http://www.w3.org/2000/svg" font-family="Noto Sans, Arial" font-size="10">']
    meses = {10: "Octubre 2026", 11: "Noviembre 2026"}
    # fondo de fines de semana y cabecera
    for i in range(dias):
        d = ini + timedelta(days=i)
        x = x0 + i * dx
        if d.weekday() >= 5:
            o.append(f'<rect x="{x:.1f}" y="{top - 14}" width="{dx:.1f}" height="{alto - top + 6}" fill="#eef2f6"/>')
        o.append(f'<text x="{x + dx / 2:.1f}" y="{top - 4}" text-anchor="middle" font-size="8" fill="#555">{d.day}</text>')
        if d.weekday() == 0:
            o.append(f'<line x1="{x:.1f}" y1="{top - 14}" x2="{x:.1f}" y2="{alto}" stroke="#c9d3de" stroke-width="0.8"/>')
    for m, txt in meses.items():
        idx = [i for i in range(dias) if (ini + timedelta(days=i)).month == m]
        if idx:
            xa, xb = x0 + idx[0] * dx, x0 + (idx[-1] + 1) * dx
            o.append(f'<rect x="{xa:.1f}" y="2" width="{xb - xa:.1f}" height="14" fill="#1F4E79"/>')
            o.append(f'<text x="{(xa + xb) / 2:.1f}" y="12.5" text-anchor="middle" fill="#fff" font-weight="700" font-size="9">{txt}</text>')
    for i, (texto, a, b, color, es_fase) in enumerate(filas):
        y = top + i * alto_fila
        if i % 2 == 0:
            o.append(f'<rect x="0" y="{y}" width="{x0}" height="{alto_fila}" fill="#f6f8fb"/>')
        peso = "700" if es_fase else "400"
        o.append(f'<text x="4" y="{y + alto_fila - 5}" font-weight="{peso}" fill="{"#1F4E79" if es_fase else "#222"}">{e(texto)}</text>')
        xa = x0 + (a - ini).days * dx
        xb = x0 + ((b - ini).days + 1) * dx
        if es_fase:
            o.append(f'<rect x="{xa:.1f}" y="{y + 6}" width="{xb - xa:.1f}" height="5" fill="#1F4E79"/>')
        else:
            o.append(f'<rect x="{xa + 1:.1f}" y="{y + 3}" width="{xb - xa - 2:.1f}" height="{alto_fila - 6}" rx="2.5" fill="{color}"/>')
    for h, d, _ in hitos:
        x = x0 + ((f(d) - ini).days + 0.5) * dx
        o.append(f'<line x1="{x:.1f}" y1="30" x2="{x:.1f}" y2="{alto}" stroke="#b03a3a" stroke-width="0.9" stroke-dasharray="3 2"/>')
        o.append(f'<path d="M{x:.1f},19 l5,5 l-5,5 l-5,-5 z" fill="#b03a3a"/>')
        o.append(f'<text x="{x + 6:.1f}" y="28" font-size="8" font-weight="700" fill="#b03a3a">{h}</text>')
    o.append("</svg>")
    return "\n".join(o)


def gantt_actividades(fases):
    filas = []
    for fase in fases:
        acts = [a for a in ACTIVIDADES if a[1] == fase]
        filas.append((f"{fase.replace('F', 'Fase ')} · {FASES[fase]}", min(f(a[6]) for a in acts), max(f(a[7]) for a in acts), "", True))
        for a in acts:
            filas.append((f"{a[0]} {a[2]} ({nombre(a[4])})", f(a[6]), f(a[7]), PERSONAS[a[4]][2], False))
    return gantt(filas, date(ANIO, 10, 7), date(ANIO, 11, 6), hitos=HITOS, alto_fila=16)


def gantt_fases():
    filas = []
    for fase, titulo in FASES.items():
        acts = [a for a in ACTIVIDADES if a[1] == fase]
        filas.append((f"{fase.replace('F', 'Fase ')} · {titulo}", min(f(a[6]) for a in acts), max(f(a[7]) for a in acts), "#2E6DA4", False))
    return gantt(filas, date(ANIO, 10, 7), date(ANIO, 11, 6), ancho=720, etiqueta=170, alto_fila=24, hitos=HITOS)


def leyenda():
    return " ".join(f'<span class="ley"><i style="background:{c}"></i>{n}</span>' for _, (_, n, c) in PERSONAS.items()) + \
        ' <span class="ley"><i style="background:#b03a3a;transform:rotate(45deg);width:8px;height:8px"></i>Hito</span>' \
        ' <span class="ley"><i style="background:#eef2f6;border:1px solid #ccd"></i>Fin de semana</span>'


# --------------------------------------------------------------------------- ensamblado
def leyenda_fases():
    return ('<span class="ley"><i style="background:#2E6DA4"></i>Duración de la fase</span>'
            ' <span class="ley"><i style="background:#b03a3a;transform:rotate(45deg);width:8px;height:8px"></i>Hito</span>'
            ' <span class="ley"><i style="background:#eef2f6;border:1px solid #ccd"></i>Fin de semana</span>')


def construir(paginas=None):
    t = PLANTILLA.read_text(encoding="utf-8")
    total_h = sum(a[8] for a in ACTIVIDADES)
    rep = {
        "ACTIVIDADES": tabla_actividades(), "CRONOGRAMA": tabla_cronograma(), "HITOS": tabla_hitos(), "CARGA": tabla_carga(),
        "GANTT_FASES": gantt_fases(), "GANTT_1": gantt_actividades(["F0", "F1", "F2", "F3"]),
        "GANTT_2": gantt_actividades(["F4", "F5", "F6", "F7", "F8", "F9", "F10"]), "LEYENDA": leyenda(), "LEYENDA_FASES": leyenda_fases(),
        "TOTAL_ACT": str(len(ACTIVIDADES)), "TOTAL_HORAS": str(total_h),
    }
    for k, v in rep.items():
        t = t.replace("{{" + k + "}}", v)
    entradas = re.findall(r'<h([23]) id="([\w-]+)"[^>]*>(.*?)</h\1>', t)
    lineas = [f'<li class="toc-{n}"><a href="#{i}"><span>{re.sub(r"<[^>]+>", "", x).strip()}</span>'
              f'<span class="toc-pag">{(paginas or {}).get(i, "00")}</span></a></li>' for n, i, x in entradas]
    t = t.replace("{{INDICE}}", "\n".join(lineas))
    t = re.sub(r'<h([23]) id="([\w-]+)"([^>]*)>', lambda m: f'<h{m.group(1)} id="{m.group(2)}"{m.group(3)}><span class="marca">QQ{m.group(2).replace("-", "")}QQ</span>', t)
    SALIDA_HTML.write_text(t, encoding="utf-8")
    return [i for _, i, _ in entradas]


if __name__ == "__main__":
    validar()
    base.SALIDA_HTML, base.SALIDA_PDF = SALIDA_HTML, SALIDA_PDF
    ids = construir()
    asyncio.run(base.imprimir_pdf())
    paginas, _ = base.paginas_de_titulos(ids)
    construir(paginas)
    asyncio.run(base.imprimir_pdf())
    _, total = base.paginas_de_titulos(ids)
    print(f"Listo: {SALIDA_PDF} ({total} páginas)")
