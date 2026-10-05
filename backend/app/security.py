"""Autenticación (bcrypt + JWT con sesiones revocables) y autorización por rol."""
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from . import config
from .db import ejecutar, get_db, uno
from .errors import APIError

ROL_ADMIN = "administrador"
ROL_JUGADOR = "jugador"

_bearer = HTTPBearer(auto_error=False)


def hash_password(texto: str) -> str:
    return bcrypt.hashpw(texto.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode()


def verificar_password(texto: str, hash_guardado: str) -> bool:
    try:
        return bcrypt.checkpw(texto.encode("utf-8"), hash_guardado.encode())
    except ValueError:
        return False


def crear_sesion(conn, usuario, ip=None, user_agent=None):
    """Registra la sesión en BD y devuelve el JWT firmado."""
    jti = str(uuid.uuid4())
    expira = datetime.now(timezone.utc) + timedelta(hours=config.JWT_EXPIRA_HORAS)
    ejecutar(conn,
             "INSERT INTO sesiones (usuario_id, jti, ip, user_agent, expira_en) "
             "VALUES (%s, %s, %s, %s, NOW() + INTERVAL %s HOUR)",
             (usuario["id"], jti, ip, (user_agent or "")[:255], config.JWT_EXPIRA_HORAS))
    token = jwt.encode(
        {"sub": str(usuario["id"]), "rol": usuario["rol"], "jti": jti, "exp": expira},
        config.JWT_SECRET, algorithm=config.JWT_ALGORITMO)
    return token, expira


def usuario_actual(request: Request,
                   cred: HTTPAuthorizationCredentials = Depends(_bearer),
                   conn=Depends(get_db)):
    if cred is None or cred.scheme.lower() != "bearer":
        raise APIError(401, "Debes iniciar sesión para continuar.")
    try:
        datos = jwt.decode(cred.credentials, config.JWT_SECRET, algorithms=[config.JWT_ALGORITMO])
    except jwt.ExpiredSignatureError:
        raise APIError(401, "Tu sesión expiró. Inicia sesión nuevamente.")
    except jwt.InvalidTokenError:
        raise APIError(401, "Token de sesión inválido.")

    fila = uno(conn, """
        SELECT u.id, u.username, u.email, u.activo, u.eliminado_en, r.nombre AS rol,
               s.revocada_en, s.expira_en < NOW() AS expirada
        FROM sesiones s
        JOIN usuarios u ON u.id = s.usuario_id
        JOIN roles r    ON r.id = u.rol_id
        WHERE s.jti = %s AND u.id = %s
    """, (datos.get("jti"), datos.get("sub")))
    if not fila or fila["revocada_en"] or fila["expirada"]:
        raise APIError(401, "Tu sesión ya no es válida. Inicia sesión nuevamente.")
    if not fila["activo"] or fila["eliminado_en"]:
        raise APIError(403, "Tu cuenta está desactivada.")

    request.state.jti = datos["jti"]
    return {"id": fila["id"], "username": fila["username"], "email": fila["email"], "rol": fila["rol"]}


def requiere_rol(*roles):
    """Dependencia que comprueba en el servidor que el rol tenga permiso para el endpoint."""
    def _verificar(usuario=Depends(usuario_actual)):
        if usuario["rol"] not in roles:
            raise APIError(403, "No tienes permisos para realizar esta operación.")
        return usuario
    return _verificar


solo_admin = requiere_rol(ROL_ADMIN)
solo_jugador = requiere_rol(ROL_JUGADOR)
es_admin = lambda usuario: usuario["rol"] == ROL_ADMIN  # noqa: E731
