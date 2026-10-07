"""/api/dashboard, /api/reportes, /api/bitacora y /api/juego/config."""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query

from .. import config
from ..db import get_db, todos, uno, valor
from ..security import es_admin, solo_admin, usuario_actual
from ..services.consultas import Filtros, orden_sql, paginar
from .perfil import items_disponibles

router = APIRouter(tags=["Dashboard y reportes"])


# ---------------------------------------------------------------- DASHBOARD
@router.get("/api/dashboard", summary="Indicadores del dashboard (cambian según el rol)")
def dashboard(usuario=Depends(usuario_actual), conn=Depends(get_db)):
    if es_admin(usuario):
        return _dashboard_admin(conn)
    return _dashboard_jugador(conn, usuario)


def _dashboard_admin(conn):
    tarjetas = uno(conn, """
        SELECT
          (SELECT COUNT(*) FROM usuarios u JOIN roles r ON r.id = u.rol_id
            WHERE r.nombre = 'jugador' AND u.activo = 1 AND u.eliminado_en IS NULL) AS jugadores_activos,
          (SELECT COUNT(*) FROM usuarios WHERE creado_en >= NOW() - INTERVAL 7 DAY) AS registros_7d,
          (SELECT COUNT(*) FROM partidas WHERE estado = 'finalizada' AND iniciada_en >= CURDATE()) AS partidas_hoy,
          (SELECT COUNT(*) FROM partidas WHERE estado = 'finalizada' AND iniciada_en >= NOW() - INTERVAL 30 DAY) AS partidas_30d,
          (SELECT COALESCE(SUM(precio_pagado), 0) FROM compras WHERE estado = 'completada'
            AND creada_en >= NOW() - INTERVAL 30 DAY) AS ventas_monedas_30d,
          (SELECT COUNT(*) FROM visualizaciones_anuncio WHERE estado = 'completada' AND completada_en >= CURDATE()) AS anuncios_hoy,
          (SELECT COALESCE(SUM(monedas), 0) FROM perfiles) AS monedas_en_circulacion,
          (SELECT COALESCE(SUM(monto), 0) FROM ordenes_pago WHERE estado = 'pagada'
            AND pagada_en >= NOW() - INTERVAL 30 DAY) AS ingresos_mxn_30d,
          (SELECT COUNT(*) FROM apuestas WHERE creada_en >= CURDATE()) AS apuestas_hoy
    """)
    tarjetas["ingresos_mxn_30d"] = float(tarjetas["ingresos_mxn_30d"])
    partidas_7d = todos(conn, """
        SELECT DATE(iniciada_en) AS dia, COUNT(*) AS partidas FROM partidas
        WHERE estado = 'finalizada' AND iniciada_en >= CURDATE() - INTERVAL 6 DAY
        GROUP BY DATE(iniciada_en) ORDER BY dia
    """)
    actividad = todos(conn, """
        SELECT b.accion, b.entidad, b.entidad_id, b.creado_en, u.username
        FROM bitacora b LEFT JOIN usuarios u ON u.id = b.usuario_id
        ORDER BY b.id DESC LIMIT 8
    """)
    alertas = []
    invalidas = valor(conn, "SELECT COUNT(*) FROM partidas WHERE estado = 'invalida' AND motivo_invalida <> 'Partida abandonada' "
                            "AND iniciada_en >= NOW() - INTERVAL 1 DAY")
    if invalidas:
        alertas.append({"nivel": "advertencia", "mensaje": f"{invalidas} partida(s) rechazadas por resultado sospechoso en las últimas 24 h."})
    sin_ventas = todos(conn, """
        SELECT i.nombre FROM items i WHERE i.activo = 1 AND i.es_gratuito = 0
          AND NOT EXISTS (SELECT 1 FROM compras c WHERE c.item_id = i.id AND c.creada_en >= NOW() - INTERVAL 30 DAY)
    """)
    for s in sin_ventas:
        alertas.append({"nivel": "info", "mensaje": f"'{s['nombre']}' no tiene ventas en los últimos 30 días."})
    if not valor(conn, "SELECT COUNT(*) FROM anuncios WHERE activo = 1"):
        alertas.append({"nivel": "advertencia", "mensaje": "No hay anuncios activos: los jugadores no pueden ganar monedas viendo publicidad."})
    return {"rol": "administrador", "tarjetas": tarjetas, "partidas_7d": partidas_7d,
            "actividad_reciente": actividad, "alertas": alertas}


def _dashboard_jugador(conn, usuario):
    uid = usuario["id"]
    tarjetas = uno(conn, """
        SELECT p.monedas,
          (SELECT COUNT(*) FROM partidas WHERE usuario_id = %(u)s AND estado = 'finalizada') AS partidas,
          (SELECT COUNT(*) FROM partidas WHERE usuario_id = %(u)s AND estado = 'finalizada' AND ganador = 'J1') AS victorias,
          (SELECT COALESCE(MAX(puntaje), 0) FROM partidas WHERE usuario_id = %(u)s AND estado = 'finalizada') AS mejor_puntaje,
          (SELECT COUNT(*) FROM usuario_logros WHERE usuario_id = %(u)s) AS logros,
          (SELECT COUNT(*) FROM logros WHERE activo = 1) AS logros_total
        FROM perfiles p WHERE p.usuario_id = %(u)s
    """, {"u": uid})
    tarjetas["porcentaje_victorias"] = round(100 * tarjetas["victorias"] / tarjetas["partidas"], 1) if tarjetas["partidas"] else 0
    vistos = valor(conn, "SELECT COUNT(*) FROM visualizaciones_anuncio WHERE usuario_id = %s AND estado = 'completada' "
                         "AND completada_en >= CURDATE()", (uid,))
    tarjetas["anuncios_restantes_hoy"] = max(0, config.ANUNCIOS_MAX_DIA - vistos)
    posicion = valor(conn, """
        SELECT COUNT(*) + 1 FROM (
          SELECT pa.usuario_id, SUM(pa.puntaje) AS total FROM partidas pa
          JOIN usuarios u ON u.id = pa.usuario_id AND u.activo = 1
          WHERE pa.estado = 'finalizada' GROUP BY pa.usuario_id) t
        WHERE t.total > (SELECT COALESCE(SUM(puntaje), 0) FROM partidas WHERE usuario_id = %s AND estado = 'finalizada')
    """, (uid,))
    tarjetas["posicion_ranking"] = posicion if tarjetas["partidas"] else None
    ultimas = todos(conn, """
        SELECT pa.id, pa.ganador, pa.puntaje, pa.monedas_ganadas, pa.duracion_ms, pa.iniciada_en,
               p1.nombre AS personaje_j1, p2.nombre AS personaje_j2
        FROM partidas pa JOIN items p1 ON p1.id = pa.personaje_j1_id JOIN items p2 ON p2.id = pa.personaje_j2_id
        WHERE pa.usuario_id = %s AND pa.estado = 'finalizada' ORDER BY pa.id DESC LIMIT 5
    """, (uid,))
    partidas_7d = todos(conn, """
        SELECT DATE(iniciada_en) AS dia, COUNT(*) AS partidas, SUM(ganador = 'J1') AS victorias FROM partidas
        WHERE usuario_id = %s AND estado = 'finalizada' AND iniciada_en >= CURDATE() - INTERVAL 6 DAY
        GROUP BY DATE(iniciada_en) ORDER BY dia
    """, (uid,))
    bloqueados = valor(conn, """
        SELECT COUNT(*) FROM items i WHERE i.activo = 1 AND i.es_gratuito = 0
          AND NOT EXISTS (SELECT 1 FROM inventario_usuario v WHERE v.item_id = i.id AND v.usuario_id = %s)
    """, (uid,))
    return {"rol": "jugador", "tarjetas": tarjetas, "ultimas_partidas": ultimas, "partidas_7d": partidas_7d,
            "articulos_por_desbloquear": bloqueados}


# ---------------------------------------------------------------- REPORTES
def _rango(desde: date | None, hasta: date | None):
    hasta = hasta or date.today()
    desde = desde or hasta - timedelta(days=29)
    return Filtros(), desde, hasta


@router.get("/api/reportes/ventas", summary="Reporte de ventas de la tienda por rango de fechas (admin)")
def reporte_ventas(desde: date | None = None, hasta: date | None = None,
                   admin=Depends(solo_admin), conn=Depends(get_db)):
    f, desde, hasta = _rango(desde, hasta)
    f.agregar("c.estado = 'completada'").rango_fechas("c.creada_en", desde, hasta)
    por_dia = todos(conn, f"SELECT DATE(c.creada_en) AS dia, COUNT(*) AS compras, SUM(c.precio_pagado) AS monedas "
                          f"FROM compras c {f.where} GROUP BY DATE(c.creada_en) ORDER BY dia", f.params)
    por_item = todos(conn, f"""
        SELECT i.nombre AS item, t.codigo AS tipo, COUNT(*) AS compras, SUM(c.precio_pagado) AS monedas
        FROM compras c JOIN items i ON i.id = c.item_id JOIN tipos_item t ON t.id = i.tipo_id
        {f.where} GROUP BY i.id, i.nombre, t.codigo ORDER BY monedas DESC
    """, f.params)
    g = Filtros().agregar("c.estado = 'reembolsada'").rango_fechas("c.creada_en", desde, hasta)
    reembolsos = valor(conn, f"SELECT COUNT(*) FROM compras c {g.where}", g.params)
    return {"desde": desde, "hasta": hasta, "por_dia": por_dia, "por_item": por_item,
            "totales": {"compras": sum(r["compras"] for r in por_item),
                        "monedas": int(sum(r["monedas"] for r in por_item)), "reembolsos": reembolsos}}


@router.get("/api/reportes/partidas", summary="Reporte de actividad de partidas por rango de fechas (admin)")
def reporte_partidas(desde: date | None = None, hasta: date | None = None,
                     admin=Depends(solo_admin), conn=Depends(get_db)):
    f, desde, hasta = _rango(desde, hasta)
    f.rango_fechas("pa.iniciada_en", desde, hasta)
    por_dia = todos(conn, f"""
        SELECT DATE(pa.iniciada_en) AS dia, SUM(pa.estado = 'finalizada') AS finalizadas,
               SUM(pa.estado = 'invalida') AS invalidas, COUNT(DISTINCT pa.usuario_id) AS jugadores
        FROM partidas pa {f.where} GROUP BY DATE(pa.iniciada_en) ORDER BY dia
    """, f.params)
    g = Filtros().agregar("pa.estado = 'finalizada'").rango_fechas("pa.iniciada_en", desde, hasta)
    por_personaje = todos(conn, f"""
        SELECT i.nombre AS personaje, COUNT(*) AS usos, SUM(pa.ganador = 'J1') AS victorias_j1
        FROM partidas pa JOIN items i ON i.id = pa.personaje_j1_id {g.where}
        GROUP BY i.id, i.nombre ORDER BY usos DESC
    """, g.params)
    mas_activos = todos(conn, f"""
        SELECT u.username, COUNT(*) AS partidas, SUM(pa.ganador = 'J1') AS victorias, SUM(pa.puntaje) AS puntaje
        FROM partidas pa JOIN usuarios u ON u.id = pa.usuario_id {g.where}
        GROUP BY u.id, u.username ORDER BY partidas DESC LIMIT 10
    """, g.params)
    resumen = uno(conn, f"SELECT COUNT(*) AS partidas, ROUND(AVG(pa.duracion_ms)) AS duracion_promedio_ms, "
                        f"ROUND(AVG(pa.puntaje)) AS puntaje_promedio FROM partidas pa {g.where}", g.params)
    return {"desde": desde, "hasta": hasta, "por_dia": por_dia, "por_personaje": por_personaje,
            "jugadores_mas_activos": mas_activos, "resumen": resumen}


@router.get("/api/reportes/economia", summary="Monedas emitidas y gastadas por tipo y rango de fechas (admin)")
def reporte_economia(desde: date | None = None, hasta: date | None = None,
                     admin=Depends(solo_admin), conn=Depends(get_db)):
    f, desde, hasta = _rango(desde, hasta)
    f.rango_fechas("m.creado_en", desde, hasta)
    por_tipo = todos(conn, f"SELECT m.tipo, COUNT(*) AS movimientos, SUM(m.monto) AS monedas "
                           f"FROM movimientos_monedas m {f.where} GROUP BY m.tipo ORDER BY m.tipo", f.params)
    anuncios = todos(conn, """
        SELECT a.titulo, COUNT(v.id) AS vistas, COALESCE(SUM(v.monedas_otorgadas), 0) AS monedas
        FROM anuncios a LEFT JOIN visualizaciones_anuncio v ON v.anuncio_id = a.id AND v.estado = 'completada'
             AND v.completada_en >= %s AND v.completada_en < %s
        GROUP BY a.id, a.titulo ORDER BY vistas DESC
    """, (desde, hasta + timedelta(days=1)))
    emitidas = int(sum(r["monedas"] for r in por_tipo if r["monedas"] > 0))
    gastadas = int(-sum(r["monedas"] for r in por_tipo if r["monedas"] < 0))
    return {"desde": desde, "hasta": hasta, "por_tipo": por_tipo, "anuncios": anuncios,
            "totales": {"emitidas": emitidas, "gastadas": gastadas, "neto": emitidas - gastadas}}


# ---------------------------------------------------------------- BITÁCORA
@router.get("/api/bitacora", summary="Historial de operaciones (admin)")
def bitacora_listar(q: str | None = Query(None, max_length=60), accion: str | None = Query(None, max_length=40),
                    entidad: str | None = Query(None, max_length=40),
                    desde: date | None = None, hasta: date | None = None,
                    orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
                    admin=Depends(solo_admin), conn=Depends(get_db)):
    f = Filtros().buscar(q, "u.username", "b.entidad_id", "b.estado_nuevo")
    f.si(accion, "b.accion = %s").si(entidad, "b.entidad = %s").rango_fechas("b.creado_en", desde, hasta)
    o = orden_sql(orden, {"fecha": "b.creado_en", "accion": "b.accion", "usuario": "u.username"}, "-fecha")
    res = paginar(conn, "SELECT b.id, u.username, b.accion, b.entidad, b.entidad_id, b.estado_anterior, b.estado_nuevo, "
                        "b.ip, b.creado_en", "FROM bitacora b LEFT JOIN usuarios u ON u.id = b.usuario_id",
                  f, o + ", b.id DESC", page, limit)
    res["acciones"] = [r["accion"] for r in todos(conn, "SELECT DISTINCT accion FROM bitacora ORDER BY accion")]
    res["entidades"] = [r["entidad"] for r in todos(conn, "SELECT DISTINCT entidad FROM bitacora ORDER BY entidad")]
    return res


# ---------------------------------------------------------------- JUEGO
@router.get("/api/juego/config", summary="Personajes desbloqueados y escenario equipado para el juego")
def juego_config(usuario=Depends(usuario_actual), conn=Depends(get_db)):
    disponibles = items_disponibles(conn, usuario["id"])
    escenario = uno(conn, "SELECT i.codigo FROM perfiles p JOIN items i ON i.id = p.escenario_equipado_id "
                          "WHERE p.usuario_id = %s AND i.activo = 1", (usuario["id"],))
    personajes = todos(conn, "SELECT i.codigo, i.nombre, i.precio, i.activo FROM items i "
                             "JOIN tipos_item t ON t.id = i.tipo_id WHERE t.codigo = 'personaje'")
    codigos = {d["codigo"] for d in disponibles}
    return {
        "usuario": usuario["username"],
        "personajes": {p["codigo"]: {"nombre": p["nombre"], "desbloqueado": p["codigo"] in codigos, "precio": p["precio"]}
                       for p in personajes},
        "escenario": escenario["codigo"] if escenario else "clasico",
    }


@router.get("/api/reportes/monetizacion", summary="Ingresos por Google Pay, apuestas y gachapón por rango de fechas (admin)")
def reporte_monetizacion(desde: date | None = None, hasta: date | None = None,
                         admin=Depends(solo_admin), conn=Depends(get_db)):
    f, desde, hasta = _rango(desde, hasta)
    f.agregar("o.estado = 'pagada'").rango_fechas("o.pagada_en", desde, hasta)
    ingresos_dia = todos(conn, f"SELECT DATE(o.pagada_en) AS dia, COUNT(*) AS ordenes, SUM(o.monto) AS monto "
                               f"FROM ordenes_pago o {f.where} GROUP BY DATE(o.pagada_en) ORDER BY dia", f.params)
    por_paquete = todos(conn, f"SELECT p.nombre AS paquete, COUNT(*) AS ordenes, SUM(o.monto) AS monto, SUM(o.monedas) AS monedas "
                              f"FROM ordenes_pago o JOIN paquetes_monedas p ON p.id = o.paquete_id {f.where} "
                              f"GROUP BY p.id, p.nombre ORDER BY monto DESC", f.params)
    g = Filtros().agregar("a.estado IN ('ganada', 'perdida')").rango_fechas("a.creada_en", desde, hasta)
    apuestas = uno(conn, f"SELECT COUNT(*) AS apuestas, COALESCE(SUM(a.monto), 0) AS apostado, COALESCE(SUM(a.pago), 0) AS pagado, "
                         f"COALESCE(SUM(a.estado = 'ganada'), 0) AS ganadas FROM apuestas a {g.where}", g.params)
    apuestas_tipo = todos(conn, f"SELECT a.tipo, COUNT(*) AS apuestas, SUM(a.monto) AS apostado, SUM(a.pago) AS pagado "
                                f"FROM apuestas a {g.where} GROUP BY a.tipo", g.params)
    h = Filtros().rango_fechas("t.creada_en", desde, hasta)
    rarezas = todos(conn, f"SELECT r.rareza, COUNT(*) AS cantidad, SUM(r.por_garantia) AS por_garantia "
                          f"FROM gacha_resultados r JOIN gacha_tiradas t ON t.id = r.tirada_id {h.where} "
                          f"GROUP BY r.rareza ORDER BY FIELD(r.rareza, 'comun', 'rara', 'epica')", h.params)
    gacha_tot = uno(conn, f"SELECT COUNT(*) AS tiradas, COALESCE(SUM(t.costo), 0) AS gastado FROM gacha_tiradas t {h.where}", h.params)
    for fila in ingresos_dia + por_paquete:
        fila["monto"] = float(fila["monto"])
    return {"desde": desde, "hasta": hasta, "ingresos_por_dia": ingresos_dia, "por_paquete": por_paquete,
            "totales": {"ingresos_mxn": round(sum(r["monto"] for r in ingresos_dia), 2),
                        "ordenes": sum(r["ordenes"] for r in ingresos_dia)},
            "apuestas": {**{k: int(v) for k, v in apuestas.items()},
                         "margen": int(apuestas["apostado"]) - int(apuestas["pagado"]), "por_tipo": apuestas_tipo},
            "gacha": {**gacha_tot, "rarezas": rarezas}}
