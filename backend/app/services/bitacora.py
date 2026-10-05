"""Historial de operaciones importantes (quién, qué, cuándo, estado anterior y nuevo)."""
from ..db import ejecutar


def _texto(valor):
    if valor is None:
        return None
    if isinstance(valor, dict):
        return "; ".join(f"{k}={v}" for k, v in valor.items())
    return str(valor)


def registrar(conn, usuario_id, accion, entidad, entidad_id=None, anterior=None, nuevo=None, ip=None):
    ejecutar(conn,
             "INSERT INTO bitacora (usuario_id, accion, entidad, entidad_id, estado_anterior, estado_nuevo, ip) "
             "VALUES (%s, %s, %s, %s, %s, %s, %s)",
             (usuario_id, accion, entidad, None if entidad_id is None else str(entidad_id),
              _texto(anterior), _texto(nuevo), ip))
