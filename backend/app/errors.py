"""Errores de la API con mensajes comprensibles. Nunca se exponen detalles internos (SQL, trazas, credenciales)."""
import logging

import pymysql
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

log = logging.getLogger("uma.api")


class APIError(Exception):
    def __init__(self, status, mensaje, codigo=None, detalles=None):
        self.status = status
        self.mensaje = mensaje
        self.codigo = codigo or _CODIGOS.get(status, "error")
        self.detalles = detalles


def no_encontrado(mensaje="El recurso solicitado no existe."):
    return APIError(404, mensaje)


def conflicto(mensaje):
    return APIError(409, mensaje)


def invalido(mensaje, detalles=None):
    return APIError(422, mensaje, detalles=detalles)


_CODIGOS = {
    400: "solicitud_incorrecta",
    401: "no_autenticado",
    403: "sin_permisos",
    404: "no_encontrado",
    405: "metodo_no_permitido",
    409: "conflicto",
    422: "validacion",
    429: "limite_alcanzado",
    500: "error_interno",
    501: "no_implementado",
    503: "servicio_no_disponible",
}

_MENSAJES_HTTP = {
    401: "Debes iniciar sesión para continuar.",
    403: "No tienes permisos para realizar esta operación.",
    404: "El recurso solicitado no existe.",
    405: "Método HTTP no permitido para esta ruta.",
}

_CAMPOS = {
    "missing": "Este campo es obligatorio.",
    "string_too_short": "Es demasiado corto.",
    "string_too_long": "Es demasiado largo.",
    "greater_than": "Debe ser mayor a {gt}.",
    "greater_than_equal": "Debe ser mayor o igual a {ge}.",
    "less_than_equal": "Debe ser menor o igual a {le}.",
    "int_parsing": "Debe ser un número entero.",
    "int_type": "Debe ser un número entero.",
    "bool_parsing": "Debe ser verdadero o falso.",
    "date_from_datetime_parsing": "Fecha inválida (usa AAAA-MM-DD).",
    "date_parsing": "Fecha inválida (usa AAAA-MM-DD).",
    "value_error": "{msg}",
    "string_pattern_mismatch": "Formato inválido.",
    "enum": "Valor no permitido.",
    "literal_error": "Valor no permitido.",
    "json_invalid": "El cuerpo de la petición no es JSON válido.",
}


def _respuesta(status, codigo, mensaje, detalles=None):
    cuerpo = {"error": {"codigo": codigo, "mensaje": mensaje}}
    if detalles:
        cuerpo["error"]["detalles"] = detalles
    return JSONResponse(status_code=status, content=cuerpo)


def registrar_manejadores(app: FastAPI):
    @app.exception_handler(APIError)
    async def _api_error(_: Request, exc: APIError):
        return _respuesta(exc.status, exc.codigo, exc.mensaje, exc.detalles)

    @app.exception_handler(RequestValidationError)
    async def _validacion(_: Request, exc: RequestValidationError):
        detalles = {}
        for err in exc.errors():
            campo = ".".join(str(p) for p in err.get("loc", []) if p not in ("body", "query", "path"))
            plantilla = _CAMPOS.get(err.get("type"), "Valor inválido.")
            ctx = dict(err.get("ctx") or {})
            ctx.setdefault("msg", str(ctx.get("error", err.get("msg", ""))).replace("Value error, ", ""))
            try:
                detalles[campo or "cuerpo"] = plantilla.format(**ctx)
            except (KeyError, IndexError):
                detalles[campo or "cuerpo"] = "Valor inválido."
        return _respuesta(422, "validacion", "Revisa los datos enviados.", detalles)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        mensaje = _MENSAJES_HTTP.get(exc.status_code, str(exc.detail))
        return _respuesta(exc.status_code, _CODIGOS.get(exc.status_code, "error"), mensaje)

    @app.exception_handler(pymysql.err.IntegrityError)
    async def _integridad(_: Request, exc):
        log.warning("IntegrityError: %s", exc)
        if exc.args and exc.args[0] == 1062:
            return _respuesta(409, "conflicto", "Ya existe un registro con esos datos.")
        return _respuesta(409, "conflicto", "La operación viola una regla de integridad de los datos.")

    @app.exception_handler(pymysql.err.OperationalError)
    async def _bd_caida(_: Request, exc):
        log.error("Error de conexión a BD: %s", exc)
        return _respuesta(503, "servicio_no_disponible",
                          "No fue posible conectar con la base de datos. Intenta más tarde.")

    @app.exception_handler(Exception)
    async def _interno(_: Request, exc: Exception):
        log.exception("Error no controlado")
        return _respuesta(500, "error_interno", "No fue posible completar la operación.")
