"""/api/tiempo-juego — monedas por tiempo de juego ACTIVO, medido por el servidor.

La página del juego envía un latido cada minuto con el número de teclas presionadas.
El servidor solo cuenta el tiempo transcurrido entre latidos reales (máx. 75 s por latido),
ignora los minutos sin actividad y paga un bloque de monedas cada 5 minutos activos,
con un tope diario.
"""
import uuid

from fastapi import APIRouter, Depends

from .. import config
from ..db import ejecutar, get_db, transaccion, uno, valor
from ..errors import APIError, conflicto, no_encontrado
from ..schemas import LatidoIn
from ..security import solo_jugador
from ..services import monedas

router = APIRouter(prefix="/api/tiempo-juego", tags=["Tiempo de juego"])

LATIDO_MIN_SEG = 45
LATIDO_MAX_CONTADO = 75


def _ganado_hoy(conn, uid):
    return int(valor(conn, "SELECT COALESCE(SUM(monto), 0) FROM movimientos_monedas WHERE usuario_id = %s "
                           "AND tipo = 'tiempo_juego' AND creado_en >= CURDATE()", (uid,)))


@router.get("/resumen", summary="Monedas ganadas hoy por tiempo de juego y reglas vigentes")
def resumen(usuario=Depends(solo_jugador), conn=Depends(get_db)):
    total = uno(conn, "SELECT COALESCE(SUM(segundos_activos), 0) AS seg FROM sesiones_juego WHERE usuario_id = %s", (usuario["id"],))
    return {"monedas_hoy": _ganado_hoy(conn, usuario["id"]), "limite_diario": config.TIEMPO_MONEDAS_MAX_DIA,
            "bloque_segundos": config.TIEMPO_BLOQUE_SEG, "monedas_por_bloque": config.TIEMPO_MONEDAS_BLOQUE,
            "minutos_totales": int(total["seg"]) // 60}


@router.post("/sesiones", status_code=201, summary="Iniciar una sesión de juego")
def iniciar(usuario=Depends(solo_jugador), conn=Depends(get_db)):
    token = str(uuid.uuid4())
    with transaccion(conn):
        # RN: solo una sesión activa por usuario (evita sumar tiempo con varias pestañas)
        ejecutar(conn, "UPDATE sesiones_juego SET estado = 'cerrada' WHERE usuario_id = %s AND estado = 'activa'", (usuario["id"],))
        ejecutar(conn, "INSERT INTO sesiones_juego (usuario_id, token) VALUES (%s, %s)", (usuario["id"], token))
    return {"token": token, "latido_segundos": 60, **resumen(usuario, conn)}


@router.post("/sesiones/{token}/latido", summary="Registrar un minuto de juego (transacción)")
def latido(token: str, datos: LatidoIn, usuario=Depends(solo_jugador), conn=Depends(get_db)):
    with transaccion(conn):
        s = uno(conn, "SELECT id, usuario_id, estado, segundos_activos, segundos_sin_pagar, "
                      "TIMESTAMPDIFF(SECOND, ultimo_latido, NOW()) AS delta FROM sesiones_juego WHERE token = %s FOR UPDATE",
                (token,))
        if not s or s["usuario_id"] != usuario["id"]:
            raise no_encontrado("La sesión de juego no existe.")
        if s["estado"] != "activa":
            raise conflicto("La sesión de juego se cerró (¿abriste el juego en otra pestaña?).")
        if s["delta"] < LATIDO_MIN_SEG:
            raise APIError(429, "Latido demasiado pronto.")
        # RN: solo cuenta tiempo con actividad y a lo más 75 s por latido
        contado = min(int(s["delta"]), LATIDO_MAX_CONTADO) if datos.interacciones > 0 else 0
        sin_pagar = s["segundos_sin_pagar"] + contado
        bloques = sin_pagar // config.TIEMPO_BLOQUE_SEG
        sin_pagar -= bloques * config.TIEMPO_BLOQUE_SEG
        disponible = max(0, config.TIEMPO_MONEDAS_MAX_DIA - _ganado_hoy(conn, usuario["id"]))
        ganadas = min(bloques * config.TIEMPO_MONEDAS_BLOQUE, disponible)
        ejecutar(conn, "UPDATE sesiones_juego SET ultimo_latido = NOW(), segundos_activos = segundos_activos + %s, "
                       "segundos_sin_pagar = %s, monedas_otorgadas = monedas_otorgadas + %s WHERE id = %s",
                 (contado, sin_pagar, ganadas, s["id"]))
        saldo = monedas.mover(conn, usuario["id"], "tiempo_juego", ganadas,
                              f"Tiempo de juego activo ({config.TIEMPO_BLOQUE_SEG // 60} min)", f"TJ-{s['id']}")
    return {"segundos_contados": contado, "monedas_ganadas": ganadas, "saldo": saldo,
            "segundos_para_siguiente": config.TIEMPO_BLOQUE_SEG - sin_pagar,
            "monedas_hoy": _ganado_hoy(conn, usuario["id"]), "limite_diario": config.TIEMPO_MONEDAS_MAX_DIA,
            "activo": contado > 0}


@router.post("/sesiones/{token}/cerrar", summary="Cerrar la sesión de juego")
def cerrar(token: str, usuario=Depends(solo_jugador), conn=Depends(get_db)):
    ejecutar(conn, "UPDATE sesiones_juego SET estado = 'cerrada' WHERE token = %s AND usuario_id = %s", (token, usuario["id"]))
    return {"mensaje": "Sesión cerrada."}
