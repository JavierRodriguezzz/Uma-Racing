"""/api/usuarios — administración de usuarios (solo administradores)."""
from fastapi import APIRouter, Depends, Query, Request

from ..db import ejecutar, get_db, todos, transaccion, uno, valor
from ..errors import conflicto, no_encontrado
from ..schemas import AjusteMonedasIn, EstadoIn, UsuarioCrearIn, UsuarioEditarIn
from ..security import solo_admin
from ..services import bitacora, monedas
from ..services.consultas import Filtros, orden_sql, paginar
from .auth import crear_usuario, ip_de

router = APIRouter(prefix="/api/usuarios", tags=["Usuarios (admin)"])

SELECT_USUARIO = """
    SELECT u.id, u.username, u.email, r.nombre AS rol, u.activo, u.creado_en, u.ultimo_acceso, u.eliminado_en,
           p.nombre_mostrar, p.monedas,
           (SELECT COUNT(*) FROM partidas pa WHERE pa.usuario_id = u.id AND pa.estado = 'finalizada') AS partidas,
           (SELECT COUNT(*) FROM compras c WHERE c.usuario_id = u.id AND c.estado = 'completada') AS compras
"""
FROM_USUARIO = "FROM usuarios u JOIN roles r ON r.id = u.rol_id JOIN perfiles p ON p.usuario_id = u.id"


def _mapear(f):
    f["activo"] = bool(f["activo"])
    return f


def _obtener(conn, uid):
    fila = uno(conn, SELECT_USUARIO + FROM_USUARIO + " WHERE u.id = %s", (uid,))
    if not fila:
        raise no_encontrado("El usuario no existe.")
    return _mapear(fila)


def _admins_activos_sin(conn, uid):
    return valor(conn, "SELECT COUNT(*) FROM usuarios u JOIN roles r ON r.id = u.rol_id "
                       "WHERE r.nombre = 'administrador' AND u.activo = 1 AND u.eliminado_en IS NULL AND u.id <> %s", (uid,))


@router.get("", summary="Listar usuarios con búsqueda, filtros, orden y paginación")
def listar(q: str | None = Query(None, max_length=60),
           rol: str | None = Query(None, pattern="^(administrador|jugador)$"),
           activo: bool | None = None, incluir_eliminados: bool = False,
           orden: str | None = None, page: int = Query(1, ge=1), limit: int = Query(15, ge=1, le=100),
           admin=Depends(solo_admin), conn=Depends(get_db)):
    f = Filtros().buscar(q, "u.username", "u.email", "p.nombre_mostrar")
    f.si(rol, "r.nombre = %s").si(activo, "u.activo = %s", int(bool(activo)))
    if not incluir_eliminados:
        f.agregar("u.eliminado_en IS NULL")
    o = orden_sql(orden, {"username": "u.username", "fecha": "u.creado_en", "monedas": "p.monedas",
                          "acceso": "u.ultimo_acceso", "partidas": "partidas"}, "username")
    return paginar(conn, SELECT_USUARIO, FROM_USUARIO, f, o, page, limit, _mapear)


@router.get("/{uid}", summary="Detalle de un usuario con su actividad reciente")
def detalle(uid: int, admin=Depends(solo_admin), conn=Depends(get_db)):
    u = _obtener(conn, uid)
    u["ultimos_movimientos"] = todos(conn, "SELECT tipo, monto, saldo_nuevo, descripcion, creado_en FROM movimientos_monedas "
                                           "WHERE usuario_id = %s ORDER BY id DESC LIMIT 10", (uid,))
    u["sesiones_activas"] = valor(conn, "SELECT COUNT(*) FROM sesiones WHERE usuario_id = %s AND revocada_en IS NULL "
                                        "AND expira_en > NOW()", (uid,))
    return u


@router.post("", status_code=201, summary="Crear usuario con rol")
def crear(datos: UsuarioCrearIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    with transaccion(conn):
        uid = crear_usuario(conn, datos, datos.rol, actor_id=admin["id"], ip=ip_de(request))
    return _obtener(conn, uid)


@router.put("/{uid}", summary="Actualizar correo, nombre y rol")
def actualizar(uid: int, datos: UsuarioEditarIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _obtener(conn, uid)
    if uno(conn, "SELECT id FROM usuarios WHERE email = %s AND id <> %s", (datos.email.lower(), uid)):
        raise conflicto("El correo electrónico ya está registrado por otro usuario.")
    # RN: no se puede quitar el rol al último administrador activo
    if antes["rol"] == "administrador" and datos.rol != "administrador" and _admins_activos_sin(conn, uid) == 0:
        raise conflicto("No puedes quitar el rol al último administrador activo.")
    with transaccion(conn):
        ejecutar(conn, "UPDATE usuarios SET email = %s, rol_id = (SELECT id FROM roles WHERE nombre = %s) WHERE id = %s",
                 (datos.email.lower(), datos.rol, uid))
        ejecutar(conn, "UPDATE perfiles SET nombre_mostrar = %s WHERE usuario_id = %s", (datos.nombre_mostrar, uid))
        if antes["rol"] != datos.rol:  # el token lleva el rol: se cierran sus sesiones
            ejecutar(conn, "UPDATE sesiones SET revocada_en = NOW() WHERE usuario_id = %s AND revocada_en IS NULL", (uid,))
        bitacora.registrar(conn, admin["id"], "actualizar", "usuarios", uid,
                           anterior={"email": antes["email"], "rol": antes["rol"], "nombre": antes["nombre_mostrar"]},
                           nuevo={"email": datos.email, "rol": datos.rol, "nombre": datos.nombre_mostrar}, ip=ip_de(request))
    return _obtener(conn, uid)


def _desactivar(conn, admin, uid, eliminar, request):
    antes = _obtener(conn, uid)
    if uid == admin["id"]:
        raise conflicto("No puedes desactivar tu propia cuenta.")
    if antes["rol"] == "administrador" and _admins_activos_sin(conn, uid) == 0:
        raise conflicto("No puedes desactivar al último administrador activo.")
    with transaccion(conn):
        ejecutar(conn, "UPDATE usuarios SET activo = 0" + (", eliminado_en = NOW()" if eliminar else "") + " WHERE id = %s", (uid,))
        ejecutar(conn, "UPDATE sesiones SET revocada_en = NOW() WHERE usuario_id = %s AND revocada_en IS NULL", (uid,))
        bitacora.registrar(conn, admin["id"], "eliminar" if eliminar else "cambiar_estado", "usuarios", uid,
                           anterior={"activo": antes["activo"]},
                           nuevo={"activo": False, "eliminado": eliminar}, ip=ip_de(request))


@router.patch("/{uid}/estado", summary="Activar o desactivar un usuario")
def cambiar_estado(uid: int, datos: EstadoIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    if datos.activo:
        antes = _obtener(conn, uid)
        if antes["eliminado_en"]:
            raise conflicto("El usuario fue eliminado; no puede reactivarse.")
        with transaccion(conn):
            ejecutar(conn, "UPDATE usuarios SET activo = 1 WHERE id = %s", (uid,))
            bitacora.registrar(conn, admin["id"], "cambiar_estado", "usuarios", uid,
                               anterior={"activo": antes["activo"]}, nuevo={"activo": True}, ip=ip_de(request))
    else:
        _desactivar(conn, admin, uid, False, request)
    return _obtener(conn, uid)


@router.delete("/{uid}", summary="Eliminar usuario (baja lógica: conserva su historial)")
def eliminar(uid: int, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    if _obtener(conn, uid)["eliminado_en"]:
        raise conflicto("El usuario ya fue eliminado.")
    _desactivar(conn, admin, uid, True, request)
    return {"mensaje": "Usuario eliminado. Sus partidas y compras se conservan en el historial."}


@router.patch("/{uid}/monedas", summary="Ajuste manual de monedas (transacción)")
def ajustar_monedas(uid: int, datos: AjusteMonedasIn, request: Request, admin=Depends(solo_admin), conn=Depends(get_db)):
    antes = _obtener(conn, uid)
    if antes["rol"] != "jugador":
        raise conflicto("Solo se pueden ajustar monedas de jugadores.")
    with transaccion(conn):
        saldo = monedas.mover(conn, uid, "ajuste", datos.monto, f"Ajuste del administrador: {datos.motivo}")
        bitacora.registrar(conn, admin["id"], "ajuste_monedas", "perfiles", uid,
                           anterior={"monedas": antes["monedas"]}, nuevo={"monedas": saldo, "motivo": datos.motivo},
                           ip=ip_de(request))
    return _obtener(conn, uid)
