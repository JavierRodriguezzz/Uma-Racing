"""/api/gacha — gachapón de corredoras, escenarios y monedas.

Probabilidades públicas por rareza (75 % común, 22 % rara, 3 % épica) y garantía:
la tirada número 30 sin épica es épica segura. Si sale un artículo que ya tienes,
recibes monedas de compensación.
"""
import uuid

from fastapi import APIRouter, Depends, Query, Request

from ..db import ejecutar, get_db, todos, transaccion, uno
from ..errors import APIError, conflicto, no_encontrado
from ..schemas import EstadoIn, PremioIn, TiradaIn
from ..security import es_admin, solo_admin, solo_jugador, usuario_actual
from ..services import bitacora, gacha, logros, monedas
from ..services.consultas import Filtros, orden_sql, paginar
from .auth import ip_de

router = APIRouter(prefix="/api/gacha", tags=["Gachapón"])

SELECT_PREMIO = """
    SELECT g.id, g.nombre, g.rareza, g.tipo, g.item_id, g.monedas, g.peso, g.monedas_repetido, g.activo,
           i.codigo AS item_codigo, i.imagen_url, t.codigo AS item_tipo
    FROM gacha_premios g LEFT JOIN items i ON i.id = g.item_id LEFT JOIN tipos_item t ON t.id = i.tipo_id
"""


def _premios_activos(conn):
    return todos(conn, SELECT_PREMIO + " WHERE g.activo = 1 ORDER BY FIELD(g.rareza, 'epica', 'rara', 'comun'), g.id")


def _poseidos(conn, uid):
    return {r["item_id"] for r in todos(conn, """
        SELECT i.id AS item_id FROM items i LEFT JOIN inventario_usuario v ON v.item_id = i.id AND v.usuario_id = %s
        WHERE i.es_gratuito = 1 OR v.id IS NOT NULL""", (uid,))}


@router.get("", summary="Premios, probabilidades, costos y contador de garantía")
def info(usuario=Depends(usuario_actual), conn=Depends(get_db)):
    premios = _premios_activos(conn)
    probs = gacha.probabilidades(premios)
    poseidos = _poseidos(conn, usuario["id"])
    for p in premios:
        p["probabilidad"] = probs[p["id"]]
        p["activo"] = bool(p["activo"])
        p["poseido"] = p["tipo"] == "item" and p["item_id"] in poseidos
    sin_epica = uno(conn, "SELECT tiradas_sin_epica FROM perfiles WHERE usuario_id = %s", (usuario["id"],))
    return {"premios": premios, "rarezas": gacha.PROB_RAREZA, "costo_1": gacha.COSTO_TIRADA, "costo_10": gacha.COSTO_DIEZ,
            "garantia": gacha.GARANTIA_EPICA, "sin_epica": sin_epica["tiradas_sin_epica"] if sin_epica else 0}


@router.post("/tiradas", status_code=201, summary="Tirar 1 o 10 veces (transacción)")
def tirar(datos: TiradaIn, request: Request, usuario=Depends(solo_jugador), conn=Depends(get_db)):
    premios = _premios_activos(conn)
    if not any(p["rareza"] == "comun" for p in premios):
        raise APIError(503, "El gachapón está en mantenimiento.")
    costo = gacha.COSTO_TIRADA if datos.cantidad == 1 else gacha.COSTO_DIEZ
    resultados = []
    with transaccion(conn):
        saldo = monedas.bloquear_saldo(conn, usuario["id"])
        if saldo < costo:
            raise conflicto(f"Saldo insuficiente: la tirada cuesta {costo} monedas y tienes {saldo}.")
        sin_epica = uno(conn, "SELECT tiradas_sin_epica FROM perfiles WHERE usuario_id = %s", (usuario["id"],))["tiradas_sin_epica"]
        tid, _ = ejecutar(conn, "INSERT INTO gacha_tiradas (folio, usuario_id, cantidad, costo) VALUES (%s, %s, %s, %s)",
                          (str(uuid.uuid4())[:24], usuario["id"], datos.cantidad, costo))
        folio = f"GCH-{tid:06d}"
        ejecutar(conn, "UPDATE gacha_tiradas SET folio = %s WHERE id = %s", (folio, tid))
        monedas.mover(conn, usuario["id"], "gacha", -costo, f"Tirada de gachapón x{datos.cantidad}", folio)
        poseidos = _poseidos(conn, usuario["id"])
        for _ in range(datos.cantidad):
            premio, garantia, sin_epica = gacha.tirar(premios, sin_epica)
            repetido = premio["tipo"] == "item" and premio["item_id"] in poseidos
            otorgadas = premio["monedas_repetido"] if repetido else (premio["monedas"] or 0)
            ejecutar(conn, "INSERT INTO gacha_resultados (tirada_id, premio_id, rareza, repetido, por_garantia, monedas_otorgadas) "
                           "VALUES (%s, %s, %s, %s, %s, %s)", (tid, premio["id"], premio["rareza"], repetido, garantia, otorgadas))
            if premio["tipo"] == "item" and not repetido:
                ejecutar(conn, "INSERT INTO inventario_usuario (usuario_id, item_id, origen) VALUES (%s, %s, 'gacha')",
                         (usuario["id"], premio["item_id"]))
                poseidos.add(premio["item_id"])
            if otorgadas:
                monedas.mover(conn, usuario["id"], "premio_gacha", otorgadas,
                              f"Gachapón: {premio['nombre']}{' (repetido)' if repetido else ''}", folio)
            resultados.append({"premio_id": premio["id"], "nombre": premio["nombre"], "rareza": premio["rareza"],
                               "tipo": premio["tipo"], "imagen_url": premio["imagen_url"], "item_codigo": premio["item_codigo"],
                               "repetido": repetido, "por_garantia": garantia, "monedas": otorgadas})
        ejecutar(conn, "UPDATE perfiles SET tiradas_sin_epica = %s WHERE usuario_id = %s", (sin_epica, usuario["id"]))
        nuevos = logros.evaluar(conn, usuario["id"])
        bitacora.registrar(conn, usuario["id"], "tirada_gacha", "gacha_tiradas", folio,
                           nuevo={"cantidad": datos.cantidad, "costo": costo,
                                  "rarezas": ",".join(r["rareza"] for r in resultados)}, ip=ip_de(request))
    return {"folio": folio, "costo": costo, "resultados": resultados, "sin_epica": sin_epica,
            "saldo": monedas.bloquear_saldo(conn, usuario["id"]), "logros_nuevos": nuevos}


@router.get("/tiradas", summary="Historial de tiradas")
def historial(rareza: str | None = Query(None, pattern="^(comun|rara|epica)$"),
              orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(15, ge=1, le=100),
              usuario=Depends(usuario_actual), conn=Depends(get_db)):
    f = Filtros()
    if not es_admin(usuario):
        f.agregar("t.usuario_id = %s", usuario["id"])
    f.si(rareza, "r.rareza = %s")
    o = orden_sql(orden, {"fecha": "t.creada_en", "rareza": "FIELD(r.rareza, 'comun', 'rara', 'epica')"}, "-fecha")
    return paginar(conn, "SELECT t.folio, u.username, t.cantidad, t.creada_en, p.nombre AS premio, r.rareza, r.repetido, "
                         "r.por_garantia, r.monedas_otorgadas",
                   "FROM gacha_resultados r JOIN gacha_tiradas t ON t.id = r.tirada_id JOIN gacha_premios p ON p.id = r.premio_id "
                   "JOIN usuarios u ON u.id = t.usuario_id", f, o + ", r.id DESC", page, limit)


# ---------------------------------------------------------------- Administración de premios
def _premio(conn, pid):
    fila = uno(conn, SELECT_PREMIO + " WHERE g.id = %s", (pid,))
    if not fila:
        raise no_encontrado("El premio no existe.")
    fila["activo"] = bool(fila["activo"])
    return fila


def _validar_premio(conn, d: PremioIn):
    if d.tipo == "item":
        if not d.item_id or not uno(conn, "SELECT id FROM items WHERE id = %s AND es_gratuito = 0", (d.item_id,)):
            raise APIError(422, "Elige un artículo de pago existente.", detalles={"item_id": "Artículo no válido."})
        d.monedas = None
    else:
        if not d.monedas:
            raise APIError(422, "Indica cuántas monedas da el premio.", detalles={"monedas": "Obligatorio."})
        d.item_id = None
    return d


@router.get("/premios", summary="Todos los premios (administrador)")
def premios_admin(admin=Depends(solo_admin), conn=Depends(get_db)):
    filas = todos(conn, SELECT_PREMIO + " ORDER BY FIELD(g.rareza, 'epica', 'rara', 'comun'), g.id")
    probs = gacha.probabilidades([f for f in filas if f["activo"]])
    for f in filas:
        f["activo"] = bool(f["activo"])
        f["probabilidad"] = probs.get(f["id"], 0)
    return {"datos": filas}


@router.post("/premios", status_code=201, summary="Crear premio (administrador)")
def crear_premio(datos: PremioIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    d = _validar_premio(conn, datos)
    with transaccion(conn):
        pid, _ = ejecutar(conn, "INSERT INTO gacha_premios (nombre, rareza, tipo, item_id, monedas, peso, monedas_repetido, activo) "
                                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                          (d.nombre, d.rareza, d.tipo, d.item_id, d.monedas, d.peso, d.monedas_repetido, d.activo))
        bitacora.registrar(conn, admin["id"], "crear", "gacha_premios", pid, nuevo=d.model_dump(), ip=ip_de(request))
    return _premio(conn, pid)


@router.put("/premios/{pid}", summary="Actualizar premio (administrador)")
def actualizar_premio(pid: int, datos: PremioIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _premio(conn, pid)
    d = _validar_premio(conn, datos)
    with transaccion(conn):
        ejecutar(conn, "UPDATE gacha_premios SET nombre = %s, rareza = %s, tipo = %s, item_id = %s, monedas = %s, peso = %s, "
                       "monedas_repetido = %s, activo = %s WHERE id = %s",
                 (d.nombre, d.rareza, d.tipo, d.item_id, d.monedas, d.peso, d.monedas_repetido, d.activo, pid))
        bitacora.registrar(conn, admin["id"], "actualizar", "gacha_premios", pid,
                           anterior={k: antes[k] for k in ("rareza", "peso", "activo")},
                           nuevo={k: getattr(d, k) for k in ("rareza", "peso", "activo")}, ip=ip_de(request))
    return _premio(conn, pid)


@router.delete("/premios/{pid}", summary="Eliminar premio (baja lógica, administrador)")
def eliminar_premio(pid: int, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _premio(conn, pid)
    if not antes["activo"]:
        raise conflicto("El premio ya está dado de baja.")
    # RN: siempre debe quedar al menos un premio común activo
    if antes["rareza"] == "comun" and not uno(conn, "SELECT id FROM gacha_premios WHERE rareza = 'comun' AND activo = 1 AND id <> %s", (pid,)):
        raise conflicto("Debe quedar al menos un premio común activo.")
    with transaccion(conn):
        ejecutar(conn, "UPDATE gacha_premios SET activo = 0 WHERE id = %s", (pid,))
        bitacora.registrar(conn, admin["id"], "eliminar", "gacha_premios", pid, nuevo={"activo": False}, ip=ip_de(request))
    return {"mensaje": "Premio dado de baja. Las tiradas anteriores se conservan."}
