"""/api/anuncios — publicidad simulada. El servidor valida la recompensa (no basta con modificar JavaScript)."""
import uuid

from fastapi import APIRouter, Depends, Query, Request

from .. import config
from ..db import ejecutar, get_db, transaccion, uno, valor
from ..errors import APIError, conflicto, no_encontrado
from ..schemas import AnuncioIn, EstadoIn
from ..security import es_admin, solo_admin, usuario_actual
from ..services import bitacora, logros, monedas
from ..services.consultas import Filtros, orden_sql, paginar
from ..services.reglas import VENTANA_ANUNCIO_MIN
from .auth import ip_de

router = APIRouter(prefix="/api/anuncios", tags=["Publicidad"])

SELECT_ANUNCIO = """
    SELECT a.id, a.titulo, a.anunciante, a.descripcion, a.color, a.duracion_seg, a.recompensa_monedas,
           a.activo, a.creado_en,
           (SELECT COUNT(*) FROM visualizaciones_anuncio v WHERE v.anuncio_id = a.id AND v.estado = 'completada') AS vistas
"""


def _vistos_hoy(conn, usuario_id):
    return valor(conn, "SELECT COUNT(*) FROM visualizaciones_anuncio WHERE usuario_id = %s "
                       "AND estado = 'completada' AND completada_en >= CURDATE()", (usuario_id,))


def _obtener(conn, anuncio_id):
    fila = uno(conn, SELECT_ANUNCIO + " FROM anuncios a WHERE a.id = %s", (anuncio_id,))
    if not fila:
        raise no_encontrado("El anuncio no existe.")
    fila["activo"] = bool(fila["activo"])
    return fila


@router.get("", summary="Listar anuncios (jugador: activos y límite diario; admin: todos con filtros)")
def listar(q: str | None = Query(None, max_length=60), activo: bool | None = None,
           orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(20, ge=1, le=100),
           usuario=Depends(usuario_actual), conn=Depends(get_db)):
    f = Filtros().buscar(q, "a.titulo", "a.anunciante")
    if es_admin(usuario):
        f.si(activo, "a.activo = %s", int(bool(activo)))
    else:
        f.agregar("a.activo = 1")
    o = orden_sql(orden, {"titulo": "a.titulo", "recompensa": "a.recompensa_monedas",
                          "duracion": "a.duracion_seg", "vistas": "vistas", "fecha": "a.creado_en"}, "-recompensa")
    res = paginar(conn, SELECT_ANUNCIO, "FROM anuncios a", f, o, page, limit)
    vistos = _vistos_hoy(conn, usuario["id"])
    res["limite_diario"] = config.ANUNCIOS_MAX_DIA
    res["vistos_hoy"] = vistos
    res["restantes_hoy"] = max(0, config.ANUNCIOS_MAX_DIA - vistos)
    return res


@router.get("/{anuncio_id}", summary="Detalle de un anuncio")
def detalle(anuncio_id: int, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    a = _obtener(conn, anuncio_id)
    if not a["activo"] and not es_admin(usuario):
        raise no_encontrado("El anuncio no existe.")
    return a


@router.post("/{anuncio_id}/ver", status_code=201, summary="Iniciar la visualización de un anuncio")
def iniciar(anuncio_id: int, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    if es_admin(usuario):
        raise APIError(403, "Las cuentas de administrador no reciben recompensas.")
    a = _obtener(conn, anuncio_id)
    if not a["activo"]:
        raise no_encontrado("El anuncio no existe.")
    # RN: máximo de anuncios recompensados por día
    if _vistos_hoy(conn, usuario["id"]) >= config.ANUNCIOS_MAX_DIA:
        raise APIError(429, f"Ya viste los {config.ANUNCIOS_MAX_DIA} anuncios con recompensa de hoy. Vuelve mañana.")
    token = str(uuid.uuid4())
    with transaccion(conn):
        # Solo una visualización en curso por usuario: las anteriores quedan rechazadas
        ejecutar(conn, "UPDATE visualizaciones_anuncio SET estado = 'rechazada' WHERE usuario_id = %s AND estado = 'iniciada'",
                 (usuario["id"],))
        ejecutar(conn, "INSERT INTO visualizaciones_anuncio (usuario_id, anuncio_id, token) VALUES (%s, %s, %s)",
                 (usuario["id"], anuncio_id, token))
    return {"token": token, "duracion_seg": a["duracion_seg"], "recompensa_monedas": a["recompensa_monedas"]}


@router.post("/visualizaciones/{token}/completar", summary="Reclamar la recompensa de un anuncio visto")
def completar(token: str, request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    # La expiración se guarda en su propia transacción para que el rechazo no se pierda con el ROLLBACK
    with transaccion(conn):
        expirada = ejecutar(conn, """
            UPDATE visualizaciones_anuncio v JOIN anuncios a ON a.id = v.anuncio_id
            SET v.estado = 'rechazada'
            WHERE v.token = %s AND v.usuario_id = %s AND v.estado = 'iniciada'
              AND v.iniciada_en < NOW(3) - INTERVAL (a.duracion_seg + %s * 60) SECOND
        """, (token, usuario["id"], VENTANA_ANUNCIO_MIN))[1]
    if expirada:
        raise conflicto("La visualización expiró. Inicia el anuncio de nuevo.")
    with transaccion(conn):
        v = uno(conn, """
            SELECT v.id, v.usuario_id, v.estado, a.titulo, a.duracion_seg, a.recompensa_monedas,
                   TIMESTAMPDIFF(MICROSECOND, v.iniciada_en, NOW(3)) / 1000000 AS segundos
            FROM visualizaciones_anuncio v JOIN anuncios a ON a.id = v.anuncio_id
            WHERE v.token = %s FOR UPDATE
        """, (token,))
        if not v or v["usuario_id"] != usuario["id"]:
            raise no_encontrado("La visualización no existe.")
        if v["estado"] == "completada":
            raise conflicto("La recompensa de este anuncio ya fue entregada.")
        if v["estado"] == "rechazada":
            raise conflicto("Esta visualización fue cancelada. Inicia el anuncio de nuevo.")
        segundos = float(v["segundos"])
        # RN: el servidor mide el tiempo; no se paga si no se vio completo
        if segundos + 0.5 < v["duracion_seg"]:
            faltan = max(1, round(v["duracion_seg"] - segundos))
            raise APIError(422, f"El anuncio no se ha visto completo. Faltan {faltan} segundo(s).")
        if _vistos_hoy(conn, usuario["id"]) >= config.ANUNCIOS_MAX_DIA:
            raise APIError(429, "Ya alcanzaste el límite diario de anuncios con recompensa.")
        ejecutar(conn, "UPDATE visualizaciones_anuncio SET estado = 'completada', completada_en = NOW(3), "
                       "monedas_otorgadas = %s WHERE id = %s", (v["recompensa_monedas"], v["id"]))
        saldo = monedas.mover(conn, usuario["id"], "anuncio", v["recompensa_monedas"],
                              f"Recompensa por anuncio: {v['titulo']}", f"AD-{v['id']}")
        nuevos = logros.evaluar(conn, usuario["id"])
        bitacora.registrar(conn, usuario["id"], "recompensa_anuncio", "visualizaciones_anuncio", v["id"],
                           anterior={"estado": "iniciada"}, nuevo={"estado": "completada", "monedas": v["recompensa_monedas"]},
                           ip=ip_de(request))
    return {"monedas_otorgadas": v["recompensa_monedas"], "saldo": monedas.bloquear_saldo(conn, usuario["id"]),
            "restantes_hoy": max(0, config.ANUNCIOS_MAX_DIA - _vistos_hoy(conn, usuario["id"])),
            "logros_nuevos": nuevos}


# ---------- CRUD administrador ----------
@router.post("", status_code=201, summary="Crear anuncio (administrador)")
def crear(datos: AnuncioIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    with transaccion(conn):
        nuevo_id, _ = ejecutar(conn, """
            INSERT INTO anuncios (titulo, anunciante, descripcion, color, duracion_seg, recompensa_monedas, activo)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (datos.titulo, datos.anunciante, datos.descripcion, datos.color, datos.duracion_seg,
              datos.recompensa_monedas, datos.activo))
        bitacora.registrar(conn, admin["id"], "crear", "anuncios", nuevo_id, nuevo=datos.model_dump(), ip=ip_de(request))
    return _obtener(conn, nuevo_id)


@router.put("/{anuncio_id}", summary="Actualizar anuncio (administrador)")
def actualizar(anuncio_id: int, datos: AnuncioIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _obtener(conn, anuncio_id)
    with transaccion(conn):
        ejecutar(conn, """
            UPDATE anuncios SET titulo = %s, anunciante = %s, descripcion = %s, color = %s, duracion_seg = %s,
                   recompensa_monedas = %s, activo = %s WHERE id = %s
        """, (datos.titulo, datos.anunciante, datos.descripcion, datos.color, datos.duracion_seg,
              datos.recompensa_monedas, datos.activo, anuncio_id))
        bitacora.registrar(conn, admin["id"], "actualizar", "anuncios", anuncio_id,
                           anterior={k: antes[k] for k in ("titulo", "duracion_seg", "recompensa_monedas", "activo")},
                           nuevo={k: getattr(datos, k) for k in ("titulo", "duracion_seg", "recompensa_monedas", "activo")},
                           ip=ip_de(request))
    return _obtener(conn, anuncio_id)


@router.patch("/{anuncio_id}/estado", summary="Activar o desactivar un anuncio (administrador)")
def cambiar_estado(anuncio_id: int, datos: EstadoIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _obtener(conn, anuncio_id)
    with transaccion(conn):
        ejecutar(conn, "UPDATE anuncios SET activo = %s WHERE id = %s", (datos.activo, anuncio_id))
        bitacora.registrar(conn, admin["id"], "cambiar_estado", "anuncios", anuncio_id,
                           anterior={"activo": antes["activo"]}, nuevo={"activo": datos.activo}, ip=ip_de(request))
    return _obtener(conn, anuncio_id)


@router.delete("/{anuncio_id}", summary="Eliminar anuncio (baja lógica, administrador)")
def eliminar(anuncio_id: int, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _obtener(conn, anuncio_id)
    if not antes["activo"]:
        raise conflicto("El anuncio ya está dado de baja.")
    with transaccion(conn):
        ejecutar(conn, "UPDATE anuncios SET activo = 0 WHERE id = %s", (anuncio_id,))
        bitacora.registrar(conn, admin["id"], "eliminar", "anuncios", anuncio_id,
                           anterior={"activo": True}, nuevo={"activo": False}, ip=ip_de(request))
    return {"mensaje": "Anuncio dado de baja. Su historial de visualizaciones se conserva."}
