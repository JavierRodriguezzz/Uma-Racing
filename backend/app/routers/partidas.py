"""/api/partidas — el juego registra cada carrera. El servidor valida el resultado y calcula puntaje y monedas."""
import uuid
from datetime import date

from fastapi import APIRouter, Depends, Query, Request

from .. import config
from ..db import ejecutar, get_db, transaccion, uno, valor
from ..errors import APIError, conflicto, no_encontrado
from ..schemas import PartidaFinIn, PartidaInicioIn
from ..security import es_admin, usuario_actual
from ..services import bitacora, logros, monedas, reglas
from ..services.consultas import Filtros, orden_sql, paginar
from .auth import ip_de
from .perfil import puede_usar

router = APIRouter(prefix="/api/partidas", tags=["Partidas"])

SELECT_PARTIDA = """
    SELECT pa.id, pa.usuario_id, u.username, pa.estado, pa.ganador, pa.duracion_ms,
           pa.pulsaciones_j1, pa.pulsaciones_j2, pa.puntaje, pa.monedas_ganadas, pa.motivo_invalida,
           p1.nombre AS personaje_j1, p2.nombre AS personaje_j2, es.nombre AS escenario,
           pa.iniciada_en, pa.finalizada_en
"""
FROM_PARTIDA = """
    FROM partidas pa
    JOIN usuarios u ON u.id = pa.usuario_id
    JOIN items p1   ON p1.id = pa.personaje_j1_id
    JOIN items p2   ON p2.id = pa.personaje_j2_id
    JOIN items es   ON es.id = pa.escenario_id
"""


def _item_por_codigo(conn, codigo, tipo):
    return uno(conn, "SELECT i.id, i.nombre FROM items i JOIN tipos_item t ON t.id = i.tipo_id "
                     "WHERE i.codigo = %s AND t.codigo = %s", (codigo, tipo))


@router.post("", status_code=201, summary="Iniciar una partida (lo llama el juego antes de la cuenta regresiva)")
def iniciar(datos: PartidaInicioIn, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    if es_admin(usuario):
        raise APIError(403, "Las cuentas de administrador no registran partidas.")
    ids = {}
    for campo, tipo in (("personaje_j1", "personaje"), ("personaje_j2", "personaje"), ("escenario", "escenario")):
        item = _item_por_codigo(conn, getattr(datos, campo), tipo)
        if not item:
            raise APIError(422, "Revisa los datos enviados.", detalles={campo: "No existe."})
        # RN: J1 solo usa lo que tiene; J2 (invitado) usa gratuitos o lo que tenga J1
        if not puede_usar(conn, usuario["id"], item["id"], tipo):
            raise APIError(403, f"{item['nombre']} está bloqueado. Cómpralo en la tienda para usarlo.")
        ids[campo] = item["id"]
    token = str(uuid.uuid4())
    with transaccion(conn):
        # Una sola partida en curso: las anteriores sin terminar quedan inválidas
        ejecutar(conn, "UPDATE partidas SET estado = 'invalida', motivo_invalida = 'Partida abandonada' "
                       "WHERE usuario_id = %s AND estado = 'en_curso'", (usuario["id"],))
        pid, _ = ejecutar(conn, """
            INSERT INTO partidas (usuario_id, token, personaje_j1_id, personaje_j2_id, escenario_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (usuario["id"], token, ids["personaje_j1"], ids["personaje_j2"], ids["escenario"]))
    return {"id": pid, "token": token}


@router.post("/{token}/finalizar", summary="Registrar el resultado de la partida (transacción)")
def finalizar(token: str, datos: PartidaFinIn, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    with transaccion(conn):
        pa = uno(conn, """
            SELECT id, usuario_id, estado, TIMESTAMPDIFF(MICROSECOND, iniciada_en, NOW(3)) DIV 1000 AS ms_servidor
            FROM partidas WHERE token = %s FOR UPDATE
        """, (token,))
        if not pa or pa["usuario_id"] != usuario["id"]:
            raise no_encontrado("La partida no existe.")
        if pa["estado"] != "en_curso":
            raise conflicto("Esta partida ya fue registrada.")

        motivo = reglas.validar_resultado_partida(datos.duracion_ms, datos.pulsaciones_j1, datos.pulsaciones_j2,
                                                  int(pa["ms_servidor"]))
        if motivo:
            ejecutar(conn, """
                UPDATE partidas SET estado = 'invalida', ganador = %s, duracion_ms = %s, pulsaciones_j1 = %s,
                       pulsaciones_j2 = %s, motivo_invalida = %s, finalizada_en = NOW(3) WHERE id = %s
            """, (datos.ganador, datos.duracion_ms, datos.pulsaciones_j1, datos.pulsaciones_j2, motivo, pa["id"]))
            bitacora.registrar(conn, usuario["id"], "partida_invalida", "partidas", pa["id"],
                               nuevo={"motivo": motivo, "duracion_ms": datos.duracion_ms}, ip=ip_de(request))
            resultado_invalido = motivo
        else:
            resultado_invalido = None
            premiadas_hoy = valor(conn, "SELECT COUNT(*) FROM partidas WHERE usuario_id = %s AND estado = 'finalizada' "
                                        "AND monedas_ganadas > 0 AND finalizada_en >= CURDATE()", (usuario["id"],))
            puntaje = reglas.calcular_puntaje(datos.ganador, datos.duracion_ms)
            ganadas = reglas.calcular_monedas_partida(datos.ganador, premiadas_hoy, config.PARTIDAS_RECOMPENSA_MAX_DIA)
            ejecutar(conn, """
                UPDATE partidas SET estado = 'finalizada', ganador = %s, duracion_ms = %s, pulsaciones_j1 = %s,
                       pulsaciones_j2 = %s, puntaje = %s, monedas_ganadas = %s, finalizada_en = NOW(3) WHERE id = %s
            """, (datos.ganador, datos.duracion_ms, datos.pulsaciones_j1, datos.pulsaciones_j2, puntaje, ganadas, pa["id"]))
            if ganadas:
                monedas.mover(conn, usuario["id"], "partida", ganadas,
                              f"Partida #{pa['id']} ({'victoria' if datos.ganador == 'J1' else 'derrota'})", f"P-{pa['id']}")
            nuevos = logros.evaluar(conn, usuario["id"])

    if resultado_invalido:
        # Se responde después del COMMIT para que el registro de la partida inválida se conserve
        raise APIError(422, f"Resultado rechazado por el servidor: {resultado_invalido}")
    return {"id": pa["id"], "puntaje": puntaje, "monedas_ganadas": ganadas,
            "limite_diario_alcanzado": ganadas == 0,
            "saldo": monedas.bloquear_saldo(conn, usuario["id"]), "logros_nuevos": nuevos}


@router.get("", summary="Historial de partidas (propias; el admin ve todas) con filtros y paginación")
def listar(q: str | None = Query(None, max_length=60),
           estado: str | None = Query(None, pattern="^(en_curso|finalizada|invalida)$"),
           ganador: str | None = Query(None, pattern="^(J1|J2)$"),
           personaje: str | None = Query(None, max_length=40),
           desde: date | None = None, hasta: date | None = None,
           orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(15, ge=1, le=100),
           usuario=Depends(usuario_actual), conn=Depends(get_db)):
    f = Filtros()
    if not es_admin(usuario):
        f.agregar("pa.usuario_id = %s", usuario["id"])
    f.buscar(q, "u.username", "p1.nombre", "p2.nombre")
    f.si(estado, "pa.estado = %s").si(ganador, "pa.ganador = %s").si(personaje, "p1.codigo = %s")
    f.rango_fechas("pa.iniciada_en", desde, hasta)
    o = orden_sql(orden, {"fecha": "pa.iniciada_en", "puntaje": "pa.puntaje", "duracion": "pa.duracion_ms",
                          "usuario": "u.username", "monedas": "pa.monedas_ganadas"}, "-fecha")
    return paginar(conn, SELECT_PARTIDA, FROM_PARTIDA, f, o + ", pa.id DESC", page, limit)


@router.get("/{partida_id}", summary="Detalle de una partida")
def detalle(partida_id: int, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    fila = uno(conn, SELECT_PARTIDA + FROM_PARTIDA + " WHERE pa.id = %s", (partida_id,))
    if not fila or (fila["usuario_id"] != usuario["id"] and not es_admin(usuario)):
        raise no_encontrado("La partida no existe.")
    return fila
