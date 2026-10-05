"""/api/logros — catálogo de logros con progreso del jugador. CRUD para administradores."""
from fastapi import APIRouter, Depends, Query, Request

from ..db import ejecutar, get_db, todos, transaccion, uno
from ..errors import conflicto, no_encontrado
from ..schemas import LogroIn
from ..security import es_admin, solo_admin, usuario_actual
from ..services import bitacora
from ..services import logros as logros_srv

router = APIRouter(prefix="/api/logros", tags=["Logros"])

CAMPOS = ("codigo", "nombre", "descripcion", "condicion", "valor_objetivo", "recompensa_monedas", "activo")


def _obtener(conn, logro_id):
    fila = uno(conn, """
        SELECT l.*, (SELECT COUNT(*) FROM usuario_logros ul WHERE ul.logro_id = l.id) AS obtenido_por
        FROM logros l WHERE l.id = %s
    """, (logro_id,))
    if not fila:
        raise no_encontrado("El logro no existe.")
    fila["activo"] = bool(fila["activo"])
    return fila


@router.get("", summary="Logros con estado y progreso del usuario")
def listar(q: str | None = Query(None, max_length=60), obtenido: bool | None = None,
           usuario=Depends(usuario_actual), conn=Depends(get_db)):
    filas = todos(conn, """
        SELECT l.id, l.codigo, l.nombre, l.descripcion, l.condicion, l.valor_objetivo, l.recompensa_monedas,
               l.activo, ul.obtenido_en,
               (SELECT COUNT(*) FROM usuario_logros x WHERE x.logro_id = l.id) AS obtenido_por
        FROM logros l
        LEFT JOIN usuario_logros ul ON ul.logro_id = l.id AND ul.usuario_id = %s
        WHERE (%s = 1 OR l.activo = 1)
        ORDER BY l.condicion, l.valor_objetivo
    """, (usuario["id"], int(es_admin(usuario))))
    progreso = logros_srv.progreso(conn, usuario["id"])
    datos = []
    for f in filas:
        f["activo"] = bool(f["activo"])
        f["obtenido"] = f["obtenido_en"] is not None
        f["progreso"] = min(progreso[f["condicion"]], f["valor_objetivo"])
        if q and q.lower() not in (f["nombre"] + f["descripcion"]).lower():
            continue
        if obtenido is not None and f["obtenido"] != obtenido:
            continue
        datos.append(f)
    return {"datos": datos, "obtenidos": sum(f["obtenido"] for f in filas), "total": len(filas)}


@router.post("", status_code=201, summary="Crear logro (administrador)")
def crear(datos: LogroIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    if uno(conn, "SELECT id FROM logros WHERE codigo = %s", (datos.codigo,)):
        raise conflicto("Ya existe un logro con ese código.")
    with transaccion(conn):
        nuevo_id, _ = ejecutar(conn, f"INSERT INTO logros ({', '.join(CAMPOS)}) VALUES ({', '.join(['%s'] * len(CAMPOS))})",
                               [getattr(datos, c) for c in CAMPOS])
        bitacora.registrar(conn, admin["id"], "crear", "logros", nuevo_id, nuevo=datos.model_dump(), ip=request.client.host)
    return _obtener(conn, nuevo_id)


@router.put("/{logro_id}", summary="Actualizar logro (administrador)")
def actualizar(logro_id: int, datos: LogroIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _obtener(conn, logro_id)
    if uno(conn, "SELECT id FROM logros WHERE codigo = %s AND id <> %s", (datos.codigo, logro_id)):
        raise conflicto("Ya existe otro logro con ese código.")
    # RN: no se cambia la condición de un logro que ya obtuvieron jugadores (alteraría el historial)
    if antes["obtenido_por"] and (antes["condicion"] != datos.condicion or antes["valor_objetivo"] != datos.valor_objetivo):
        raise conflicto("No se puede cambiar la condición ni la meta de un logro que ya obtuvieron jugadores.")
    with transaccion(conn):
        ejecutar(conn, f"UPDATE logros SET {', '.join(f'{c} = %s' for c in CAMPOS)} WHERE id = %s",
                 [*[getattr(datos, c) for c in CAMPOS], logro_id])
        bitacora.registrar(conn, admin["id"], "actualizar", "logros", logro_id,
                           anterior={c: antes[c] for c in CAMPOS}, nuevo=datos.model_dump(), ip=request.client.host)
    return _obtener(conn, logro_id)


@router.delete("/{logro_id}", summary="Eliminar logro (baja lógica, administrador)")
def eliminar(logro_id: int, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _obtener(conn, logro_id)
    if not antes["activo"]:
        raise conflicto("El logro ya está dado de baja.")
    with transaccion(conn):
        ejecutar(conn, "UPDATE logros SET activo = 0 WHERE id = %s", (logro_id,))
        bitacora.registrar(conn, admin["id"], "eliminar", "logros", logro_id,
                           anterior={"activo": True}, nuevo={"activo": False}, ip=request.client.host)
    return {"mensaje": "Logro dado de baja. Quienes ya lo obtuvieron lo conservan."}
