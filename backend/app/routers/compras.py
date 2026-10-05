"""/api/compras — compra de items con monedas virtuales (operación transaccional) y reembolsos."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from ..db import ejecutar, get_db, transaccion, uno
from ..errors import APIError, conflicto, no_encontrado
from ..schemas import CompraIn, ReembolsoIn
from ..security import es_admin, solo_admin, usuario_actual
from ..services import bitacora, logros, monedas
from ..services.consultas import Filtros, orden_sql, paginar
from .auth import ip_de

router = APIRouter(prefix="/api/compras", tags=["Tienda — Compras"])

SELECT_COMPRA = """
    SELECT c.id, c.folio, c.usuario_id, u.username, c.item_id, i.nombre AS item, i.codigo AS item_codigo,
           t.codigo AS tipo, c.precio_pagado, c.estado, c.creada_en, c.reembolsada_en,
           ra.username AS reembolsada_por, c.motivo_reembolso
"""
FROM_COMPRA = """
    FROM compras c
    JOIN usuarios u   ON u.id = c.usuario_id
    JOIN items i      ON i.id = c.item_id
    JOIN tipos_item t ON t.id = i.tipo_id
    LEFT JOIN usuarios ra ON ra.id = c.reembolsada_por
"""


def _por_folio(conn, folio):
    fila = uno(conn, SELECT_COMPRA + FROM_COMPRA + " WHERE c.folio = %s", (folio,))
    if not fila:
        raise no_encontrado("La compra no existe.")
    return fila


@router.post("", status_code=201, summary="Comprar un item (transacción)")
def comprar(datos: CompraIn, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    """INICIO TRANSACCIÓN → bloquear saldo → validar reglas → registrar compra → agregar al inventario
    → descontar monedas + movimiento → evaluar logros → bitácora → COMMIT (o ROLLBACK si algo falla)."""
    if es_admin(usuario):
        raise APIError(403, "Las cuentas de administrador no pueden comprar artículos.")
    with transaccion(conn):
        saldo = monedas.bloquear_saldo(conn, usuario["id"])
        item = uno(conn, "SELECT id, nombre, codigo, precio, es_gratuito, activo FROM items WHERE id = %s",
                   (datos.item_id,))
        if not item or not item["activo"]:
            raise no_encontrado("El artículo no existe o ya no está a la venta.")
        if item["es_gratuito"]:
            raise conflicto("Este artículo es gratuito; ya está disponible para ti.")
        if uno(conn, "SELECT id FROM inventario_usuario WHERE usuario_id = %s AND item_id = %s",
               (usuario["id"], item["id"])):
            raise conflicto("Ya tienes este artículo en tu inventario.")
        if saldo < item["precio"]:
            raise conflicto(f"Saldo insuficiente: tienes {saldo} monedas y el artículo cuesta {item['precio']}.")

        compra_id, _ = ejecutar(conn,
                                "INSERT INTO compras (folio, usuario_id, item_id, precio_pagado) VALUES (%s, %s, %s, %s)",
                                (str(uuid.uuid4())[:24], usuario["id"], item["id"], item["precio"]))
        folio = f"UMA-{compra_id:06d}"
        ejecutar(conn, "UPDATE compras SET folio = %s WHERE id = %s", (folio, compra_id))
        ejecutar(conn, "INSERT INTO inventario_usuario (usuario_id, item_id, compra_id, origen) VALUES (%s, %s, %s, 'compra')",
                 (usuario["id"], item["id"], compra_id))
        saldo_nuevo = monedas.mover(conn, usuario["id"], "compra", -item["precio"], f"Compra de {item['nombre']}", folio)
        nuevos_logros = logros.evaluar(conn, usuario["id"])
        bitacora.registrar(conn, usuario["id"], "compra", "compras", folio,
                           anterior={"saldo": saldo},
                           nuevo={"item": item["codigo"], "precio": item["precio"], "saldo": saldo_nuevo},
                           ip=ip_de(request))
    compra = _por_folio(conn, folio)
    compra["saldo"] = monedas.bloquear_saldo(conn, usuario["id"])
    compra["logros_nuevos"] = nuevos_logros
    return compra


@router.get("", summary="Historial de compras (propias; el admin ve todas)")
def listar(q: str | None = Query(None, max_length=60),
           estado: str | None = Query(None, pattern="^(completada|reembolsada)$"),
           tipo: str | None = Query(None, pattern="^(personaje|escenario)$"),
           desde: date | None = None, hasta: date | None = None,
           orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(15, ge=1, le=100),
           usuario=Depends(usuario_actual), conn=Depends(get_db)):
    f = Filtros()
    if not es_admin(usuario):
        f.agregar("c.usuario_id = %s", usuario["id"])
    f.buscar(q, "c.folio", "u.username", "i.nombre")
    f.si(estado, "c.estado = %s").si(tipo, "t.codigo = %s").rango_fechas("c.creada_en", desde, hasta)
    o = orden_sql(orden, {"fecha": "c.creada_en", "precio": "c.precio_pagado", "folio": "c.folio",
                          "usuario": "u.username", "item": "i.nombre"}, "-fecha")
    return paginar(conn, SELECT_COMPRA, FROM_COMPRA, f, o, page, limit)


@router.get("/{folio}", summary="Detalle de una compra por folio")
def detalle(folio: str, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    compra = _por_folio(conn, folio)
    if compra["usuario_id"] != usuario["id"] and not es_admin(usuario):
        raise no_encontrado("La compra no existe.")  # no revela compras ajenas
    return compra


@router.post("/{folio}/reembolso", summary="Reembolsar una compra (administrador, transacción)")
def reembolsar(folio: str, datos: ReembolsoIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    with transaccion(conn):
        compra = uno(conn, "SELECT id, usuario_id, item_id, precio_pagado, estado FROM compras WHERE folio = %s FOR UPDATE",
                     (folio,))
        if not compra:
            raise no_encontrado("La compra no existe.")
        if compra["estado"] != "completada":
            raise conflicto("Esta compra ya fue reembolsada.")
        ejecutar(conn, "UPDATE compras SET estado = 'reembolsada', reembolsada_en = NOW(), reembolsada_por = %s, "
                       "motivo_reembolso = %s WHERE id = %s", (admin["id"], datos.motivo, compra["id"]))
        ejecutar(conn, "DELETE FROM inventario_usuario WHERE usuario_id = %s AND item_id = %s",
                 (compra["usuario_id"], compra["item_id"]))
        # Si lo tenía equipado o como favorito, vuelve a los valores gratuitos
        ejecutar(conn, """
            UPDATE perfiles SET
              escenario_equipado_id = IF(escenario_equipado_id = %(item)s,
                  (SELECT i.id FROM items i JOIN tipos_item t ON t.id = i.tipo_id
                   WHERE t.codigo = 'escenario' AND i.es_gratuito = 1 AND i.activo = 1 ORDER BY i.id LIMIT 1),
                  escenario_equipado_id),
              personaje_favorito_id = IF(personaje_favorito_id = %(item)s, NULL, personaje_favorito_id)
            WHERE usuario_id = %(u)s
        """, {"item": compra["item_id"], "u": compra["usuario_id"]})
        monedas.mover(conn, compra["usuario_id"], "reembolso", compra["precio_pagado"], f"Reembolso de la compra {folio}", folio)
        bitacora.registrar(conn, admin["id"], "reembolso", "compras", folio,
                           anterior={"estado": "completada"}, nuevo={"estado": "reembolsada", "motivo": datos.motivo},
                           ip=ip_de(request))
    return _por_folio(conn, folio)
