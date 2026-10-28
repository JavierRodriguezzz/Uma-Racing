"""/api/items — catálogo de la tienda (personajes, escenarios, chibis y muebles). CRUD para administradores."""
from fastapi import APIRouter, Depends, Query, Request

from ..db import ejecutar, get_db, todos, transaccion, uno, valor
from ..errors import conflicto, no_encontrado
from ..schemas import EstadoIn, ItemIn
from ..security import es_admin, solo_admin, usuario_actual
from ..services import bitacora
from ..services.consultas import Filtros, orden_sql, paginar
from .auth import ip_de

router = APIRouter(prefix="/api/items", tags=["Tienda — Items"])

SELECT_ITEM = """
    SELECT i.id, t.codigo AS tipo, i.codigo, i.nombre, i.descripcion, i.precio, i.es_gratuito, i.solo_gacha,
           i.imagen_url, i.activo, i.creado_en, i.actualizado_en,
           (i.es_gratuito = 1 OR inv.id IS NOT NULL) AS poseido,
           (SELECT COUNT(*) FROM compras c WHERE c.item_id = i.id AND c.estado = 'completada') AS ventas
"""
FROM_ITEM = """
    FROM items i
    JOIN tipos_item t ON t.id = i.tipo_id
    LEFT JOIN inventario_usuario inv ON inv.item_id = i.id AND inv.usuario_id = %s
"""

ORDENES = {"nombre": "i.nombre", "precio": "i.precio", "fecha": "i.creado_en", "tipo": "t.id",
           "ventas": "ventas"}


def _mapear(fila):
    for k in ("es_gratuito", "solo_gacha", "activo", "poseido"):
        fila[k] = bool(fila[k])
    return fila


def _obtener(conn, item_id, usuario_id):
    fila = uno(conn, SELECT_ITEM + FROM_ITEM + " WHERE i.id = %s", (usuario_id, item_id))
    if not fila:
        raise no_encontrado("El artículo no existe.")
    return _mapear(fila)


@router.get("", summary="Listar items con búsqueda, filtros, orden y paginación")
def listar(q: str | None = Query(None, max_length=60),
           tipo: str | None = Query(None, pattern="^(personaje|escenario|chibi|mueble)$"),
           seccion: str | None = Query(None, pattern="^(juego|dormitorio)$",
                                       description="juego: personajes y escenarios; dormitorio: chibis y muebles"),
           gratuito: bool | None = None, poseido: bool | None = None,
           precio_min: int | None = Query(None, ge=0), precio_max: int | None = Query(None, ge=0),
           activo: bool | None = None,
           orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(12, ge=1, le=100),
           usuario=Depends(usuario_actual), conn=Depends(get_db)):
    f = Filtros()
    f.params.append(usuario["id"])  # parámetro del LEFT JOIN de inventario
    f.buscar(q, "i.nombre", "i.codigo", "i.descripcion")
    f.si(tipo, "t.codigo = %s")
    if seccion:
        f.agregar("t.codigo IN ('personaje', 'escenario')" if seccion == "juego" else "t.codigo IN ('chibi', 'mueble')")
    f.si(gratuito, "i.es_gratuito = %s", int(bool(gratuito)))
    f.si(precio_min, "i.precio >= %s")
    f.si(precio_max, "i.precio <= %s")
    if poseido is not None:
        f.agregar("(i.es_gratuito = 1 OR inv.id IS NOT NULL) = %s", int(poseido))
    # RN: los jugadores solo ven artículos activos; el admin puede filtrar
    if es_admin(usuario):
        f.si(activo, "i.activo = %s", int(bool(activo)))
    else:
        f.agregar("i.activo = 1")

    # El COUNT necesita el mismo JOIN; paginar() lo antepone con los mismos parámetros
    return paginar(conn, SELECT_ITEM, FROM_ITEM, f, orden_sql(orden, ORDENES, "tipo") + ", i.precio, i.id",
                   page, limit, _mapear)


@router.get("/{item_id}", summary="Detalle de un item")
def detalle(item_id: int, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    item = _obtener(conn, item_id, usuario["id"])
    if not item["activo"] and not es_admin(usuario):
        raise no_encontrado("El artículo no existe.")
    if es_admin(usuario):
        item["ultimas_compras"] = todos(conn, """
            SELECT c.folio, u.username, c.precio_pagado, c.estado, c.creada_en
            FROM compras c JOIN usuarios u ON u.id = c.usuario_id
            WHERE c.item_id = %s ORDER BY c.creada_en DESC LIMIT 10
        """, (item_id,))
    return item


def _tipo_id(conn, tipo):
    return valor(conn, "SELECT id FROM tipos_item WHERE codigo = %s", (tipo,))


def _normalizar(datos: ItemIn):
    """RN: un item gratuito tiene precio 0; uno exclusivo del gachapón no se vende (precio 0);
    uno de pago debe costar más de 0."""
    if datos.es_gratuito and datos.solo_gacha:
        from ..errors import invalido
        raise invalido("Un artículo no puede ser gratuito y exclusivo del gachapón a la vez.",
                       {"solo_gacha": "Desmarca una de las dos opciones."})
    if datos.es_gratuito or datos.solo_gacha:
        datos.precio = 0
    elif datos.precio <= 0:
        from ..errors import invalido
        raise invalido("Un artículo de pago debe tener precio mayor a 0.", {"precio": "Debe ser mayor a 0."})
    return datos


def _verificar_minimos(conn, item_id, nuevo_activo, nuevo_gratuito):
    """RN: siempre deben quedar 2 personajes gratuitos activos y 1 escenario gratuito activo
    (son los que puede usar un jugador nuevo y el Jugador 2 invitado)."""
    actual = uno(conn, "SELECT t.codigo AS tipo, i.activo, i.es_gratuito FROM items i "
                       "JOIN tipos_item t ON t.id = i.tipo_id WHERE i.id = %s", (item_id,))
    if not actual or actual["tipo"] not in ("personaje", "escenario") or not (actual["activo"] and actual["es_gratuito"]):
        return
    if nuevo_activo and nuevo_gratuito:
        return
    minimo = 2 if actual["tipo"] == "personaje" else 1
    restantes = valor(conn, "SELECT COUNT(*) FROM items i JOIN tipos_item t ON t.id = i.tipo_id "
                            "WHERE t.codigo = %s AND i.activo = 1 AND i.es_gratuito = 1 AND i.id <> %s",
                      (actual["tipo"], item_id))
    if restantes < minimo:
        raise conflicto(f"Debe haber al menos {minimo} {actual['tipo']}(s) gratuito(s) activo(s).")


@router.post("", status_code=201, summary="Crear item (administrador)")
def crear(datos: ItemIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    datos = _normalizar(datos)
    if uno(conn, "SELECT id FROM items WHERE codigo = %s", (datos.codigo,)):
        raise conflicto("Ya existe un artículo con ese código.")
    with transaccion(conn):
        nuevo_id, _ = ejecutar(conn, """
            INSERT INTO items (tipo_id, codigo, nombre, descripcion, precio, es_gratuito, solo_gacha, imagen_url, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (_tipo_id(conn, datos.tipo), datos.codigo, datos.nombre, datos.descripcion, datos.precio,
              datos.es_gratuito, datos.solo_gacha, datos.imagen_url, datos.activo))
        bitacora.registrar(conn, admin["id"], "crear", "items", nuevo_id, nuevo=datos.model_dump(), ip=ip_de(request))
    return _obtener(conn, nuevo_id, admin["id"])


@router.put("/{item_id}", summary="Actualizar item completo (administrador)")
def actualizar(item_id: int, datos: ItemIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    datos = _normalizar(datos)
    antes = _obtener(conn, item_id, admin["id"])
    if uno(conn, "SELECT id FROM items WHERE codigo = %s AND id <> %s", (datos.codigo, item_id)):
        raise conflicto("Ya existe otro artículo con ese código.")
    if antes["tipo"] != datos.tipo and antes["ventas"]:
        raise conflicto("No se puede cambiar el tipo de un artículo que ya tiene ventas.")
    _verificar_minimos(conn, item_id, datos.activo, datos.es_gratuito)
    with transaccion(conn):
        ejecutar(conn, """
            UPDATE items SET tipo_id = %s, codigo = %s, nombre = %s, descripcion = %s, precio = %s,
                   es_gratuito = %s, solo_gacha = %s, imagen_url = %s, activo = %s
            WHERE id = %s
        """, (_tipo_id(conn, datos.tipo), datos.codigo, datos.nombre, datos.descripcion, datos.precio,
              datos.es_gratuito, datos.solo_gacha, datos.imagen_url, datos.activo, item_id))
        bitacora.registrar(conn, admin["id"], "actualizar", "items", item_id,
                           anterior={k: antes[k] for k in ("nombre", "precio", "es_gratuito", "solo_gacha", "activo")},
                           nuevo={k: getattr(datos, k) for k in ("nombre", "precio", "es_gratuito", "solo_gacha", "activo")},
                           ip=ip_de(request))
    return _obtener(conn, item_id, admin["id"])


@router.patch("/{item_id}/estado", summary="Activar o desactivar un item (administrador)")
def cambiar_estado(item_id: int, datos: EstadoIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _obtener(conn, item_id, admin["id"])
    _verificar_minimos(conn, item_id, datos.activo, antes["es_gratuito"])
    with transaccion(conn):
        ejecutar(conn, "UPDATE items SET activo = %s WHERE id = %s", (datos.activo, item_id))
        bitacora.registrar(conn, admin["id"], "cambiar_estado", "items", item_id,
                           anterior={"activo": antes["activo"]}, nuevo={"activo": datos.activo}, ip=ip_de(request))
    return _obtener(conn, item_id, admin["id"])


@router.delete("/{item_id}", summary="Eliminar item (baja lógica, administrador)")
def eliminar(item_id: int, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    """Baja lógica: el item queda inactivo para conservar el historial de compras y partidas."""
    antes = _obtener(conn, item_id, admin["id"])
    if not antes["activo"]:
        raise conflicto("El artículo ya está dado de baja.")
    _verificar_minimos(conn, item_id, False, antes["es_gratuito"])
    with transaccion(conn):
        ejecutar(conn, "UPDATE items SET activo = 0 WHERE id = %s", (item_id,))
        bitacora.registrar(conn, admin["id"], "eliminar", "items", item_id,
                           anterior={"activo": True}, nuevo={"activo": False}, ip=ip_de(request))
    return {"mensaje": "Artículo dado de baja. Los jugadores que ya lo compraron lo conservan en su historial."}
