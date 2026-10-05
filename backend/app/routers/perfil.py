"""/api/perfil — perfil del usuario autenticado, inventario, monedero y estadísticas propias."""
from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from ..db import ejecutar, get_db, todos, transaccion, uno, valor
from ..errors import APIError, invalido, no_encontrado
from ..schemas import EquiparIn, PasswordIn, PerfilIn
from ..security import hash_password, usuario_actual, verificar_password
from ..services import bitacora
from ..services import logros as logros_srv
from ..services.consultas import Filtros, orden_sql, paginar
from .auth import ip_de

router = APIRouter(prefix="/api/perfil", tags=["Perfil"])

ITEMS_DISPONIBLES_SQL = """
    SELECT i.id, i.codigo, i.nombre, i.descripcion, i.imagen_url, t.codigo AS tipo, i.es_gratuito,
           CASE WHEN i.es_gratuito = 1 THEN 'gratuito' ELSE inv.origen END AS origen,
           inv.adquirido_en
    FROM items i
    JOIN tipos_item t ON t.id = i.tipo_id
    LEFT JOIN inventario_usuario inv ON inv.item_id = i.id AND inv.usuario_id = %s
    WHERE i.activo = 1 AND (i.es_gratuito = 1 OR inv.id IS NOT NULL)
"""


def items_disponibles(conn, usuario_id):
    return todos(conn, ITEMS_DISPONIBLES_SQL + " ORDER BY t.id, i.precio, i.id", (usuario_id,))


def puede_usar(conn, usuario_id, item_id, tipo):
    """RN: solo se usan items gratuitos o que estén en el inventario del usuario."""
    return uno(conn, ITEMS_DISPONIBLES_SQL + " AND i.id = %s AND t.codigo = %s",
               (usuario_id, item_id, tipo)) is not None


@router.get("", summary="Perfil, monedas y estadísticas del usuario")
def obtener(usuario=Depends(usuario_actual), conn=Depends(get_db)):
    perfil = uno(conn, """
        SELECT p.nombre_mostrar, p.biografia, p.monedas, p.personaje_favorito_id, p.escenario_equipado_id,
               fav.nombre AS personaje_favorito, esc.nombre AS escenario_equipado, esc.codigo AS escenario_codigo,
               u.creado_en, u.ultimo_acceso
        FROM perfiles p
        JOIN usuarios u ON u.id = p.usuario_id
        LEFT JOIN items fav ON fav.id = p.personaje_favorito_id
        LEFT JOIN items esc ON esc.id = p.escenario_equipado_id
        WHERE p.usuario_id = %s
    """, (usuario["id"],))
    if not perfil:
        raise no_encontrado("El perfil no existe.")
    stats = uno(conn, """
        SELECT COUNT(*) AS partidas, COALESCE(SUM(ganador = 'J1'), 0) AS victorias,
               COALESCE(MAX(puntaje), 0) AS mejor_puntaje, COALESCE(SUM(puntaje), 0) AS puntaje_total,
               MIN(CASE WHEN ganador = 'J1' THEN duracion_ms END) AS mejor_tiempo_ms
        FROM partidas WHERE usuario_id = %s AND estado = 'finalizada'
    """, (usuario["id"],))
    stats["logros"] = valor(conn, "SELECT COUNT(*) FROM usuario_logros WHERE usuario_id = %s", (usuario["id"],))
    stats["logros_total"] = valor(conn, "SELECT COUNT(*) FROM logros WHERE activo = 1")
    stats["porcentaje_victorias"] = round(100 * int(stats["victorias"]) / stats["partidas"], 1) if stats["partidas"] else 0
    return {"usuario": usuario, "perfil": perfil, "estadisticas": stats}


@router.put("", summary="Actualizar el perfil")
def actualizar(datos: PerfilIn, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    if datos.personaje_favorito_id and not puede_usar(conn, usuario["id"], datos.personaje_favorito_id, "personaje"):
        raise invalido("Solo puedes elegir como favorito un personaje que tengas.",
                       {"personaje_favorito_id": "Personaje no disponible."})
    with transaccion(conn):
        antes = uno(conn, "SELECT nombre_mostrar, biografia, personaje_favorito_id FROM perfiles WHERE usuario_id = %s",
                    (usuario["id"],))
        ejecutar(conn, "UPDATE perfiles SET nombre_mostrar = %s, biografia = %s, personaje_favorito_id = %s "
                       "WHERE usuario_id = %s",
                 (datos.nombre_mostrar, datos.biografia, datos.personaje_favorito_id, usuario["id"]))
        bitacora.registrar(conn, usuario["id"], "actualizar_perfil", "perfiles", usuario["id"],
                           anterior=antes, nuevo=datos.model_dump(), ip=ip_de(request))
    return obtener(usuario, conn)


@router.patch("/password", summary="Cambiar la contraseña (cierra las demás sesiones)")
def cambiar_password(datos: PasswordIn, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    actual = valor(conn, "SELECT password_hash FROM usuarios WHERE id = %s", (usuario["id"],))
    if not verificar_password(datos.actual, actual):
        raise APIError(422, "La contraseña actual no es correcta.", detalles={"actual": "Incorrecta."})
    if datos.actual == datos.nueva:
        raise invalido("La nueva contraseña debe ser diferente a la actual.", {"nueva": "Igual a la actual."})
    with transaccion(conn):
        ejecutar(conn, "UPDATE usuarios SET password_hash = %s WHERE id = %s", (hash_password(datos.nueva), usuario["id"]))
        ejecutar(conn, "UPDATE sesiones SET revocada_en = NOW() WHERE usuario_id = %s AND jti <> %s AND revocada_en IS NULL",
                 (usuario["id"], request.state.jti))
        bitacora.registrar(conn, usuario["id"], "cambiar_password", "usuarios", usuario["id"], ip=ip_de(request))
    return {"mensaje": "Contraseña actualizada. Se cerraron tus otras sesiones."}


@router.get("/inventario", summary="Personajes y escenarios que el usuario puede usar")
def inventario(usuario=Depends(usuario_actual), conn=Depends(get_db)):
    equipado = valor(conn, "SELECT escenario_equipado_id FROM perfiles WHERE usuario_id = %s", (usuario["id"],))
    datos = items_disponibles(conn, usuario["id"])
    for d in datos:
        d["equipado"] = d["id"] == equipado
    return {"datos": datos}


@router.patch("/escenario", summary="Equipar un escenario")
def equipar_escenario(datos: EquiparIn, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    if not puede_usar(conn, usuario["id"], datos.item_id, "escenario"):
        raise APIError(403, "Ese escenario no está en tu inventario.")
    with transaccion(conn):
        antes = valor(conn, "SELECT escenario_equipado_id FROM perfiles WHERE usuario_id = %s FOR UPDATE", (usuario["id"],))
        ejecutar(conn, "UPDATE perfiles SET escenario_equipado_id = %s WHERE usuario_id = %s", (datos.item_id, usuario["id"]))
        bitacora.registrar(conn, usuario["id"], "equipar_escenario", "perfiles", usuario["id"],
                           anterior={"escenario_id": antes}, nuevo={"escenario_id": datos.item_id}, ip=ip_de(request))
    return {"mensaje": "Escenario equipado.", "escenario_id": datos.item_id}


@router.get("/movimientos", summary="Movimientos del monedero (paginado, filtros por tipo y fechas)")
def movimientos(tipo: str | None = Query(None, pattern="^(registro|compra|reembolso|anuncio|partida|logro|ajuste)$"),
                desde: date | None = None, hasta: date | None = None,
                orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(15, ge=1, le=100),
                usuario=Depends(usuario_actual), conn=Depends(get_db)):
    f = Filtros().agregar("usuario_id = %s", usuario["id"]).si(tipo, "tipo = %s").rango_fechas("creado_en", desde, hasta)
    o = orden_sql(orden, {"fecha": "creado_en", "monto": "monto"}, "-fecha") + ", id DESC"
    return paginar(conn, "SELECT id, tipo, monto, saldo_anterior, saldo_nuevo, referencia, descripcion, creado_en",
                   "FROM movimientos_monedas", f, o, page, limit)


@router.get("/estadisticas", summary="Estadísticas propias para gráficas (por día y por personaje)")
def estadisticas(desde: date | None = None, hasta: date | None = None,
                 usuario=Depends(usuario_actual), conn=Depends(get_db)):
    f = Filtros().agregar("pa.usuario_id = %s", usuario["id"]).agregar("pa.estado = 'finalizada'") \
        .rango_fechas("pa.iniciada_en", desde, hasta)
    por_dia = todos(conn, f"""
        SELECT DATE(pa.iniciada_en) AS dia, COUNT(*) AS partidas, SUM(pa.ganador = 'J1') AS victorias,
               ROUND(AVG(pa.puntaje)) AS puntaje_promedio
        FROM partidas pa {f.where} GROUP BY DATE(pa.iniciada_en) ORDER BY dia
    """, f.params)
    por_personaje = todos(conn, f"""
        SELECT i.nombre AS personaje, COUNT(*) AS partidas, SUM(pa.ganador = 'J1') AS victorias
        FROM partidas pa JOIN items i ON i.id = pa.personaje_j1_id {f.where}
        GROUP BY i.id, i.nombre ORDER BY partidas DESC
    """, f.params)
    return {"por_dia": por_dia, "por_personaje": por_personaje,
            "progreso_logros": logros_srv.progreso(conn, usuario["id"])}
