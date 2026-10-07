"""/api/apuestas — apuestas con monedas virtuales.

  - Carrera simulada: el jugador elige una de las 4 corredoras; el SERVIDOR simula la carrera,
    decide la ganadora y paga según el momio. El navegador solo anima el resultado recibido.
  - Reto de tiempo: el jugador apuesta a que, como Jugador 1, gana su próxima partida real en
    menos de X segundos. Se resuelve automáticamente al registrar esa partida.

Juego responsable: monto mínimo/máximo y límite de pérdida neta diaria.
"""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from .. import config
from ..db import ejecutar, get_db, todos, transaccion, uno, valor
from ..errors import APIError, conflicto, no_encontrado
from ..schemas import ApuestaCarreraIn, ApuestaTiempoIn
from ..security import es_admin, solo_jugador, usuario_actual
from ..services import bitacora, monedas, simulador
from ..services.consultas import Filtros, orden_sql, paginar
from .auth import ip_de

router = APIRouter(prefix="/api/apuestas", tags=["Apuestas"])


def corredoras(conn):
    return todos(conn, """
        SELECT i.id, i.codigo, i.nombre, i.imagen_url, a.velocidad, a.resistencia, a.arranque
        FROM atributos_carrera a JOIN items i ON i.id = a.item_id ORDER BY i.id
    """)


def _perdida_hoy(conn, uid):
    """Pérdida neta del día: lo apostado hoy menos lo cobrado (las pendientes cuentan como apostadas)."""
    return int(valor(conn, "SELECT COALESCE(SUM(monto) - SUM(pago), 0) FROM apuestas WHERE usuario_id = %s "
                           "AND creada_en >= CURDATE() AND estado <> 'cancelada'", (uid,)))


def _validar_monto(conn, uid, monto):
    if not config.APUESTA_MIN <= monto <= config.APUESTA_MAX:
        raise APIError(422, f"La apuesta debe ser de {config.APUESTA_MIN} a {config.APUESTA_MAX} monedas.",
                       detalles={"monto": f"Entre {config.APUESTA_MIN} y {config.APUESTA_MAX}."})
    if _perdida_hoy(conn, uid) + monto > config.APUESTA_PERDIDA_MAX_DIA:
        raise APIError(429, f"Alcanzaste el límite de juego responsable ({config.APUESTA_PERDIDA_MAX_DIA} monedas por día). Vuelve mañana.")


def _folio(conn, apuesta_id):
    folio = f"BET-{apuesta_id:06d}"
    ejecutar(conn, "UPDATE apuestas SET folio = %s WHERE id = %s", (folio, apuesta_id))
    return folio


def _limites(conn, uid):
    return {"minimo": config.APUESTA_MIN, "maximo": config.APUESTA_MAX,
            "perdida_max_dia": config.APUESTA_PERDIDA_MAX_DIA,
            "disponible_hoy": max(0, config.APUESTA_PERDIDA_MAX_DIA - _perdida_hoy(conn, uid))}


# ---------------------------------------------------------------- Carrera simulada
@router.get("/carrera", summary="Corredoras, atributos y momios de la carrera simulada")
def info_carrera(usuario=Depends(usuario_actual), conn=Depends(get_db)):
    cs = corredoras(conn)
    m = simulador.momios(cs)
    for c in cs:
        c.update(m[c["id"]])
    return {"corredoras": cs, "limites": _limites(conn, usuario["id"])}


@router.post("/carrera", status_code=201, summary="Apostar a una carrera simulada (transacción)")
def apostar_carrera(datos: ApuestaCarreraIn, request: Request, usuario=Depends(solo_jugador), conn=Depends(get_db)):
    cs = corredoras(conn)
    elegida = next((c for c in cs if c["id"] == datos.item_id), None)
    if not elegida:
        raise APIError(422, "Esa corredora no participa en la carrera.", detalles={"item_id": "No válida."})
    momio = simulador.momios(cs)[elegida["id"]]["momio"]
    _validar_monto(conn, usuario["id"], datos.monto)
    with transaccion(conn):
        monedas.bloquear_saldo(conn, usuario["id"])
        aid, _ = ejecutar(conn, "INSERT INTO apuestas (folio, usuario_id, tipo, monto, item_id, momio) VALUES (%s, %s, 'carrera', %s, %s, %s)",
                          (str(uuid.uuid4())[:24], usuario["id"], datos.monto, elegida["id"], momio))
        folio = _folio(conn, aid)
        monedas.mover(conn, usuario["id"], "apuesta", -datos.monto, f"Apuesta a {elegida['nombre']}", folio)
        # El servidor decide la carrera
        carrera = simulador.simular(cs)
        ganadora = next(c for c in cs if c["id"] == carrera["orden"][0])
        gano = ganadora["id"] == elegida["id"]
        pago = int(datos.monto * momio) if gano else 0
        ejecutar(conn, "UPDATE apuestas SET estado = %s, pago = %s, ganador_id = %s, resultado = %s, resuelta_en = NOW() WHERE id = %s",
                 ("ganada" if gano else "perdida", pago, ganadora["id"], f"Ganó {ganadora['nombre']}", aid))
        saldo = monedas.mover(conn, usuario["id"], "premio_apuesta", pago, f"Premio de apuesta: ganó {ganadora['nombre']}", folio)
        bitacora.registrar(conn, usuario["id"], "apuesta", "apuestas", folio,
                           nuevo={"tipo": "carrera", "monto": datos.monto, "eleccion": elegida["codigo"],
                                  "ganadora": ganadora["codigo"], "pago": pago}, ip=ip_de(request))
    return {"folio": folio, "monto": datos.monto, "momio": momio, "eleccion": elegida["id"], "ganadora": ganadora["id"],
            "gano": gano, "pago": pago, "saldo": saldo, "carrera": carrera, "limites": _limites(conn, usuario["id"])}


# ---------------------------------------------------------------- Reto de tiempo
def _duraciones_ganadas(conn, uid):
    filas = todos(conn, "SELECT duracion_ms FROM partidas WHERE usuario_id = %s AND estado = 'finalizada' AND ganador = 'J1' "
                        "ORDER BY id DESC LIMIT 50", (uid,))
    return [f["duracion_ms"] for f in filas]


@router.get("/tiempo/cotizar", summary="Momio para un reto de tiempo según tu historial")
def cotizar_tiempo(objetivo_s: float = Query(ge=8, le=90), usuario=Depends(usuario_actual), conn=Depends(get_db)):
    historial = _duraciones_ganadas(conn, usuario["id"])
    momio, p = simulador.momio_tiempo(int(objetivo_s * 1000), historial)
    pendiente = uno(conn, "SELECT folio, monto, objetivo_ms, momio, creada_en FROM apuestas WHERE usuario_id = %s "
                          "AND tipo = 'tiempo' AND estado = 'pendiente'", (usuario["id"],))
    return {"objetivo_s": objetivo_s, "momio": momio, "probabilidad_estimada": p, "victorias_consideradas": len(historial),
            "mejor_tiempo_ms": min(historial) if historial else None, "pendiente": pendiente, "limites": _limites(conn, usuario["id"])}


@router.post("/tiempo", status_code=201, summary="Apostar a ganar la próxima partida en menos de X segundos")
def apostar_tiempo(datos: ApuestaTiempoIn, request: Request, usuario=Depends(solo_jugador), conn=Depends(get_db)):
    if uno(conn, "SELECT id FROM apuestas WHERE usuario_id = %s AND tipo = 'tiempo' AND estado = 'pendiente'", (usuario["id"],)):
        raise conflicto("Ya tienes un reto de tiempo pendiente. Juega una partida o cancélalo.")
    _validar_monto(conn, usuario["id"], datos.monto)
    objetivo_ms = int(datos.objetivo_s * 1000)
    momio, _ = simulador.momio_tiempo(objetivo_ms, _duraciones_ganadas(conn, usuario["id"]))
    with transaccion(conn):
        monedas.bloquear_saldo(conn, usuario["id"])
        aid, _ = ejecutar(conn, "INSERT INTO apuestas (folio, usuario_id, tipo, monto, objetivo_ms, momio) VALUES (%s, %s, 'tiempo', %s, %s, %s)",
                          (str(uuid.uuid4())[:24], usuario["id"], datos.monto, objetivo_ms, momio))
        folio = _folio(conn, aid)
        saldo = monedas.mover(conn, usuario["id"], "apuesta", -datos.monto, f"Reto de tiempo: ganar en menos de {datos.objetivo_s:g} s", folio)
        bitacora.registrar(conn, usuario["id"], "apuesta", "apuestas", folio,
                           nuevo={"tipo": "tiempo", "monto": datos.monto, "objetivo_ms": objetivo_ms, "momio": momio}, ip=ip_de(request))
    return {"folio": folio, "monto": datos.monto, "objetivo_ms": objetivo_ms, "momio": momio, "saldo": saldo}


@router.delete("/{folio}", summary="Cancelar un reto de tiempo que aún no se juega (devuelve las monedas)")
def cancelar(folio: str, request: Request, usuario=Depends(solo_jugador), conn=Depends(get_db)):
    with transaccion(conn):
        a = uno(conn, "SELECT id, usuario_id, tipo, monto, estado, partida_id FROM apuestas WHERE folio = %s FOR UPDATE", (folio,))
        if not a or a["usuario_id"] != usuario["id"]:
            raise no_encontrado("La apuesta no existe.")
        if a["tipo"] != "tiempo" or a["estado"] != "pendiente":
            raise conflicto("Solo se pueden cancelar retos de tiempo pendientes.")
        if a["partida_id"]:
            raise conflicto("La partida de este reto ya empezó; no se puede cancelar.")
        ejecutar(conn, "UPDATE apuestas SET estado = 'cancelada', resuelta_en = NOW(), resultado = 'Cancelada por el jugador' WHERE id = %s", (a["id"],))
        saldo = monedas.mover(conn, usuario["id"], "premio_apuesta", a["monto"], "Devolución de reto de tiempo cancelado", folio)
        bitacora.registrar(conn, usuario["id"], "cancelar_apuesta", "apuestas", folio,
                           anterior={"estado": "pendiente"}, nuevo={"estado": "cancelada"}, ip=ip_de(request))
    return {"mensaje": "Reto cancelado. Se devolvieron tus monedas.", "saldo": saldo}


def vincular_reto(conn, usuario_id, partida_id):
    """Al iniciar una partida, el reto de tiempo pendiente queda ligado a ella (ya no se puede cancelar)."""
    ejecutar(conn, "UPDATE apuestas SET partida_id = %s WHERE usuario_id = %s AND tipo = 'tiempo' AND estado = 'pendiente' "
                   "AND partida_id IS NULL", (partida_id, usuario_id))


def resolver_reto(conn, usuario_id, partida_id, ganador, duracion_ms, valida):
    """Se llama dentro de la transacción de finalizar partida."""
    a = uno(conn, "SELECT id, folio, monto, objetivo_ms, momio FROM apuestas WHERE usuario_id = %s AND partida_id = %s "
                  "AND tipo = 'tiempo' AND estado = 'pendiente' FOR UPDATE", (usuario_id, partida_id))
    if not a:
        return None
    gano = valida and ganador == "J1" and duracion_ms <= a["objetivo_ms"]
    pago = int(a["monto"] * float(a["momio"])) if gano else 0
    if not valida:
        texto = "Perdida: la partida fue rechazada por el servidor"
    elif ganador != "J1":
        texto = "Perdida: ganó el Jugador 2"
    else:
        texto = f"{'Ganada' if gano else 'Perdida'}: tiempo {duracion_ms / 1000:.2f} s (objetivo {a['objetivo_ms'] / 1000:g} s)"
    ejecutar(conn, "UPDATE apuestas SET estado = %s, pago = %s, resultado = %s, resuelta_en = NOW() WHERE id = %s",
             ("ganada" if gano else "perdida", pago, texto, a["id"]))
    monedas.mover(conn, usuario_id, "premio_apuesta", pago, f"Premio de reto de tiempo {a['folio']}", a["folio"])
    return {"folio": a["folio"], "gano": gano, "pago": pago, "resultado": texto}


# ---------------------------------------------------------------- Historial
@router.get("", summary="Historial de apuestas con filtros (propias; el admin ve todas)")
def listar(q: str | None = Query(None, max_length=60),
           tipo: str | None = Query(None, pattern="^(carrera|tiempo)$"),
           estado: str | None = Query(None, pattern="^(pendiente|ganada|perdida|cancelada)$"),
           desde: date | None = None, hasta: date | None = None,
           orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(15, ge=1, le=100),
           usuario=Depends(usuario_actual), conn=Depends(get_db)):
    f = Filtros()
    if not es_admin(usuario):
        f.agregar("a.usuario_id = %s", usuario["id"])
    f.buscar(q, "a.folio", "u.username").si(tipo, "a.tipo = %s").si(estado, "a.estado = %s").rango_fechas("a.creada_en", desde, hasta)
    o = orden_sql(orden, {"fecha": "a.creada_en", "monto": "a.monto", "pago": "a.pago", "momio": "a.momio"}, "-fecha")
    res = paginar(conn, "SELECT a.folio, u.username, a.tipo, a.monto, a.momio, a.estado, a.pago, a.objetivo_ms, a.resultado, "
                        "e.nombre AS eleccion, a.creada_en, a.resuelta_en",
                  "FROM apuestas a JOIN usuarios u ON u.id = a.usuario_id LEFT JOIN items e ON e.id = a.item_id",
                  f, o + ", a.id DESC", page, limit)
    for r in res["datos"]:
        r["momio"] = float(r["momio"])
    if not es_admin(usuario):
        res["limites"] = _limites(conn, usuario["id"])
    return res
