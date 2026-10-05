"""/api/auth — registro, inicio y cierre de sesión."""
from fastapi import APIRouter, Depends, Request

from .. import config
from ..db import ejecutar, get_db, transaccion, uno
from ..errors import APIError, conflicto
from ..schemas import LoginIn, RegistroIn
from ..security import ROL_JUGADOR, crear_sesion, hash_password, usuario_actual, verificar_password
from ..services import bitacora, monedas

router = APIRouter(prefix="/api/auth", tags=["Autenticación"])


def ip_de(request: Request):
    return request.client.host if request.client else None


def crear_usuario(conn, datos, rol: str, actor_id=None, ip=None):
    """Crea usuario + perfil + bono de bienvenida. Debe llamarse dentro de una transacción."""
    if uno(conn, "SELECT id FROM usuarios WHERE username = %s", (datos.username,)):
        raise conflicto("El nombre de usuario ya está registrado.")
    if uno(conn, "SELECT id FROM usuarios WHERE email = %s", (datos.email.lower(),)):
        raise conflicto("El correo electrónico ya está registrado.")
    uid, _ = ejecutar(conn,
                      "INSERT INTO usuarios (rol_id, username, email, password_hash) "
                      "VALUES ((SELECT id FROM roles WHERE nombre = %s), %s, %s, %s)",
                      (rol, datos.username, datos.email.lower(), hash_password(datos.password)))
    ejecutar(conn,
             "INSERT INTO perfiles (usuario_id, nombre_mostrar, escenario_equipado_id) "
             "VALUES (%s, %s, (SELECT i.id FROM items i JOIN tipos_item t ON t.id = i.tipo_id "
             "                 WHERE t.codigo = 'escenario' AND i.es_gratuito = 1 AND i.activo = 1 "
             "                 ORDER BY i.id LIMIT 1))",
             (uid, datos.nombre_mostrar or datos.username))
    if rol == ROL_JUGADOR and config.MONEDAS_REGISTRO > 0:
        monedas.mover(conn, uid, "registro", config.MONEDAS_REGISTRO, "Bono de bienvenida")
    bitacora.registrar(conn, actor_id or uid, "registro", "usuarios", uid,
                       nuevo={"username": datos.username, "rol": rol}, ip=ip)
    return uid


@router.post("/registro", status_code=201, summary="Registrar una cuenta de jugador (público)")
def registro(datos: RegistroIn, request: Request, conn=Depends(get_db)):
    with transaccion(conn):
        uid = crear_usuario(conn, datos, ROL_JUGADOR, ip=ip_de(request))
    return {"id": uid, "username": datos.username, "mensaje": "Cuenta creada. Ya puedes iniciar sesión."}


@router.post("/login", summary="Iniciar sesión y obtener un token (público)")
def login(datos: LoginIn, request: Request, conn=Depends(get_db)):
    fila = uno(conn, """
        SELECT u.id, u.username, u.email, u.password_hash, u.activo, u.eliminado_en, r.nombre AS rol
        FROM usuarios u JOIN roles r ON r.id = u.rol_id
        WHERE u.username = %s OR u.email = %s
    """, (datos.usuario, datos.usuario.lower()))
    # Mismo mensaje si no existe o la contraseña es incorrecta: no revela qué cuentas existen
    if not fila or not verificar_password(datos.password, fila["password_hash"]):
        raise APIError(401, "Usuario o contraseña incorrectos.")
    if not fila["activo"] or fila["eliminado_en"]:
        raise APIError(403, "Tu cuenta está desactivada. Contacta al administrador.")
    with transaccion(conn):
        token, expira = crear_sesion(conn, fila, ip_de(request), request.headers.get("user-agent"))
        ejecutar(conn, "UPDATE usuarios SET ultimo_acceso = NOW() WHERE id = %s", (fila["id"],))
        bitacora.registrar(conn, fila["id"], "login", "sesiones", None, ip=ip_de(request))
    return {
        "token": token,
        "expira_en": expira.isoformat(),
        "usuario": {"id": fila["id"], "username": fila["username"], "rol": fila["rol"]},
    }


@router.post("/logout", summary="Cerrar sesión (revoca el token en el servidor)")
def logout(request: Request, usuario=Depends(usuario_actual), conn=Depends(get_db)):
    with transaccion(conn):
        ejecutar(conn, "UPDATE sesiones SET revocada_en = NOW() WHERE jti = %s AND revocada_en IS NULL",
                 (request.state.jti,))
        bitacora.registrar(conn, usuario["id"], "logout", "sesiones", None, ip=ip_de(request))
    return {"mensaje": "Sesión cerrada."}


@router.get("/me", summary="Usuario de la sesión actual")
def me(usuario=Depends(usuario_actual), conn=Depends(get_db)):
    perfil = uno(conn, "SELECT nombre_mostrar, monedas FROM perfiles WHERE usuario_id = %s", (usuario["id"],))
    return {**usuario, **(perfil or {})}
