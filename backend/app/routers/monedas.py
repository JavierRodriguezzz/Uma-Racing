"""/api/paquetes y /api/pagos — compra de monedas con Google Pay.

Flujo (el navegador nunca decide el precio):
  1. POST /api/pagos/ordenes {paquete_id}      → el servidor crea la orden con el monto del paquete.
  2. El navegador abre Google Pay con ese monto y obtiene un PaymentData con token.
  3. POST /api/pagos/ordenes/{folio}/confirmar → el servidor valida la orden y el token y,
     en una transacción, marca la orden como pagada y acredita las monedas.

En modo TEST Google Pay entrega tokens de prueba y no se cobra nada. En PRODUCTION el token
tendría que enviarse a una pasarela (Stripe, Conekta, etc.) antes de acreditar: está fuera del alcance.
"""
import hashlib
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from .. import config
from ..db import ejecutar, get_db, todos, transaccion, uno
from ..errors import APIError, conflicto, no_encontrado
from ..schemas import EstadoIn, GooglePayConfirmarIn, OrdenIn, PaqueteIn
from ..security import es_admin, solo_admin, usuario_actual
from ..services import bitacora, monedas
from ..services.consultas import Filtros, orden_sql, paginar
from .auth import ip_de

router = APIRouter(tags=["Monedas con Google Pay"])

REDES_PERMITIDAS = {"VISA", "MASTERCARD", "AMEX", "DISCOVER", "JCB"}


def _paquete(conn, pid):
    fila = uno(conn, "SELECT *, monedas + bonus AS total FROM paquetes_monedas WHERE id = %s", (pid,))
    if not fila:
        raise no_encontrado("El paquete no existe.")
    fila["activo"], fila["destacado"] = bool(fila["activo"]), bool(fila["destacado"])
    fila["precio_mxn"] = float(fila["precio_mxn"])
    return fila


# ---------------------------------------------------------------- Paquetes
@router.get("/api/paquetes", summary="Paquetes de monedas a la venta")
def paquetes(usuario=Depends(usuario_actual), conn=Depends(get_db)):
    filtro = "" if es_admin(usuario) else "WHERE activo = 1"
    filas = todos(conn, f"""
        SELECT p.*, p.monedas + p.bonus AS total,
               (SELECT COUNT(*) FROM ordenes_pago o WHERE o.paquete_id = p.id AND o.estado = 'pagada') AS vendidos
        FROM paquetes_monedas p {filtro} ORDER BY p.precio_mxn
    """)
    for f in filas:
        f["activo"], f["destacado"], f["precio_mxn"] = bool(f["activo"]), bool(f["destacado"]), float(f["precio_mxn"])
    return {"datos": filas, "entorno": config.GOOGLE_PAY_ENTORNO,
            "comercio": config.GOOGLE_PAY_COMERCIO, "merchant_id": config.GOOGLE_PAY_MERCHANT_ID}


@router.post("/api/paquetes", status_code=201, summary="Crear paquete (administrador)")
def crear_paquete(datos: PaqueteIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    with transaccion(conn):
        pid, _ = ejecutar(conn, "INSERT INTO paquetes_monedas (nombre, monedas, bonus, precio_mxn, destacado, activo) "
                                "VALUES (%s, %s, %s, %s, %s, %s)",
                          (datos.nombre, datos.monedas, datos.bonus, datos.precio_mxn, datos.destacado, datos.activo))
        bitacora.registrar(conn, admin["id"], "crear", "paquetes_monedas", pid, nuevo=datos.model_dump(), ip=ip_de(request))
    return _paquete(conn, pid)


@router.put("/api/paquetes/{pid}", summary="Actualizar paquete (administrador)")
def actualizar_paquete(pid: int, datos: PaqueteIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _paquete(conn, pid)
    with transaccion(conn):
        ejecutar(conn, "UPDATE paquetes_monedas SET nombre = %s, monedas = %s, bonus = %s, precio_mxn = %s, destacado = %s, "
                       "activo = %s WHERE id = %s",
                 (datos.nombre, datos.monedas, datos.bonus, datos.precio_mxn, datos.destacado, datos.activo, pid))
        bitacora.registrar(conn, admin["id"], "actualizar", "paquetes_monedas", pid,
                           anterior={k: antes[k] for k in ("monedas", "bonus", "precio_mxn", "activo")},
                           nuevo={k: getattr(datos, k) for k in ("monedas", "bonus", "precio_mxn", "activo")}, ip=ip_de(request))
    return _paquete(conn, pid)


@router.patch("/api/paquetes/{pid}/estado", summary="Activar o desactivar paquete (administrador)")
def estado_paquete(pid: int, datos: EstadoIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _paquete(conn, pid)
    with transaccion(conn):
        ejecutar(conn, "UPDATE paquetes_monedas SET activo = %s WHERE id = %s", (datos.activo, pid))
        bitacora.registrar(conn, admin["id"], "cambiar_estado", "paquetes_monedas", pid,
                           anterior={"activo": antes["activo"]}, nuevo={"activo": datos.activo}, ip=ip_de(request))
    return _paquete(conn, pid)


@router.delete("/api/paquetes/{pid}", summary="Eliminar paquete (baja lógica, administrador)")
def eliminar_paquete(pid: int, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    if not _paquete(conn, pid)["activo"]:
        raise conflicto("El paquete ya está dado de baja.")
    with transaccion(conn):
        ejecutar(conn, "UPDATE paquetes_monedas SET activo = 0 WHERE id = %s", (pid,))
        bitacora.registrar(conn, admin["id"], "eliminar", "paquetes_monedas", pid, nuevo={"activo": False}, ip=ip_de(request))
    return {"mensaje": "Paquete dado de baja. Las órdenes pagadas se conservan."}


# ---------------------------------------------------------------- Órdenes de pago
def _orden(conn, folio):
    fila = uno(conn, """
        SELECT o.id, o.folio, o.usuario_id, u.username, o.paquete_id, p.nombre AS paquete, o.monedas, o.monto, o.moneda,
               o.proveedor, o.entorno, o.estado, o.red_tarjeta, o.creada_en, o.expira_en, o.pagada_en,
               o.expira_en < NOW() AS vencida
        FROM ordenes_pago o JOIN paquetes_monedas p ON p.id = o.paquete_id JOIN usuarios u ON u.id = o.usuario_id
        WHERE o.folio = %s
    """, (folio,))
    if not fila:
        raise no_encontrado("La orden de pago no existe.")
    fila["monto"] = float(fila["monto"])
    return fila


@router.post("/api/pagos/ordenes", status_code=201, summary="Crear orden de pago para un paquete")
def crear_orden(datos: OrdenIn, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    if es_admin(usuario):
        raise APIError(403, "Las cuentas de administrador no compran monedas.")
    paquete = _paquete(conn, datos.paquete_id)
    if not paquete["activo"]:
        raise no_encontrado("El paquete ya no está a la venta.")
    with transaccion(conn):
        # RN: una sola orden pendiente por usuario; las anteriores se cancelan
        ejecutar(conn, "UPDATE ordenes_pago SET estado = 'cancelada' WHERE usuario_id = %s AND estado = 'pendiente'",
                 (usuario["id"],))
        oid, _ = ejecutar(conn, """
            INSERT INTO ordenes_pago (folio, usuario_id, paquete_id, monedas, monto, entorno, expira_en)
            VALUES (%s, %s, %s, %s, %s, %s, NOW() + INTERVAL %s MINUTE)
        """, (str(uuid.uuid4())[:24], usuario["id"], paquete["id"], paquete["total"], paquete["precio_mxn"],
              config.GOOGLE_PAY_ENTORNO, config.ORDEN_PAGO_MINUTOS))
        folio = f"PAY-{oid:06d}"
        ejecutar(conn, "UPDATE ordenes_pago SET folio = %s WHERE id = %s", (folio, oid))
    orden = _orden(conn, folio)
    # Lo que el navegador necesita para armar el PaymentDataRequest de Google Pay
    orden["transaccion"] = {"totalPriceStatus": "FINAL", "totalPrice": f"{orden['monto']:.2f}",
                            "currencyCode": orden["moneda"], "countryCode": "MX"}
    return orden


def _validar_payment_data(pd: GooglePayConfirmarIn):
    """Valida la estructura del PaymentData de Google Pay (API v2)."""
    if pd.apiVersion != 2:
        raise APIError(422, "Versión de Google Pay no soportada.")
    pmd = pd.paymentMethodData
    tok = (pmd.get("tokenizationData") or {})
    info = pmd.get("info") or {}
    if pmd.get("type") != "CARD" or tok.get("type") != "PAYMENT_GATEWAY":
        raise APIError(422, "El método de pago recibido no es válido.")
    token = tok.get("token")
    if not isinstance(token, str) or not token or len(token) > 20_000:
        raise APIError(422, "El token de pago está vacío o es inválido.")
    red = str(info.get("cardNetwork", "")).upper()
    if red and red not in REDES_PERMITIDAS:
        raise APIError(422, "Red de tarjeta no admitida.")
    return token, red or None


@router.post("/api/pagos/ordenes/{folio}/confirmar", summary="Confirmar el pago de Google Pay y acreditar monedas (transacción)")
def confirmar(folio: str, datos: GooglePayConfirmarIn, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    token, red = _validar_payment_data(datos)
    if config.GOOGLE_PAY_ENTORNO != "TEST":
        # Aquí se enviaría el token a la pasarela de pago para hacer el cargo real.
        raise APIError(501, "El cobro real requiere integrar una pasarela de pago.")
    with transaccion(conn):
        orden = uno(conn, "SELECT id, usuario_id, monedas, monto, estado, expira_en < NOW() AS vencida "
                          "FROM ordenes_pago WHERE folio = %s FOR UPDATE", (folio,))
        if not orden or orden["usuario_id"] != usuario["id"]:
            raise no_encontrado("La orden de pago no existe.")
        if orden["estado"] == "pagada":
            raise conflicto("Esta orden ya fue pagada.")
        if orden["estado"] != "pendiente":
            raise conflicto("La orden fue cancelada. Inicia la compra de nuevo.")
        if orden["vencida"]:
            ejecutar(conn, "UPDATE ordenes_pago SET estado = 'expirada' WHERE id = %s", (orden["id"],))
            vencida = True
        else:
            vencida = False
            referencia = hashlib.sha256(f"{folio}:{token}".encode()).hexdigest()
            ejecutar(conn, "UPDATE ordenes_pago SET estado = 'pagada', pagada_en = NOW(), referencia_pago = %s, red_tarjeta = %s "
                           "WHERE id = %s", (referencia, red, orden["id"]))
            saldo = monedas.mover(conn, usuario["id"], "compra_monedas", orden["monedas"],
                                  f"Compra con Google Pay ({config.GOOGLE_PAY_ENTORNO}): {orden['monedas']} monedas", folio)
            bitacora.registrar(conn, usuario["id"], "pago_confirmado", "ordenes_pago", folio,
                               anterior={"estado": "pendiente"},
                               nuevo={"estado": "pagada", "monto": orden["monto"], "monedas": orden["monedas"]}, ip=ip_de(request))
    if vencida:
        raise conflicto("La orden expiró. Inicia la compra de nuevo.")
    return {**_orden(conn, folio), "saldo": saldo}


@router.get("/api/pagos/ordenes", summary="Historial de compras de monedas (propias; el admin ve todas)")
def ordenes(q: str | None = Query(None, max_length=60),
            estado: str | None = Query(None, pattern="^(pendiente|pagada|cancelada|expirada)$"),
            desde: date | None = None, hasta: date | None = None,
            orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(15, ge=1, le=100),
            usuario=Depends(usuario_actual), conn=Depends(get_db)):
    f = Filtros()
    if not es_admin(usuario):
        f.agregar("o.usuario_id = %s", usuario["id"])
    f.buscar(q, "o.folio", "u.username", "p.nombre").si(estado, "o.estado = %s").rango_fechas("o.creada_en", desde, hasta)
    o = orden_sql(orden, {"fecha": "o.creada_en", "monto": "o.monto", "usuario": "u.username"}, "-fecha")
    res = paginar(conn, "SELECT o.folio, u.username, p.nombre AS paquete, o.monedas, o.monto, o.moneda, o.entorno, o.estado, "
                        "o.red_tarjeta, o.creada_en, o.pagada_en",
                  "FROM ordenes_pago o JOIN usuarios u ON u.id = o.usuario_id JOIN paquetes_monedas p ON p.id = o.paquete_id",
                  f, o, page, limit)
    for r in res["datos"]:
        r["monto"] = float(r["monto"])
    return res
