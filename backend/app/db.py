"""Acceso a MariaDB con PyMySQL. Todas las consultas usan parámetros (%s) para evitar SQL Injection."""
from contextlib import contextmanager

import pymysql
from pymysql.cursors import DictCursor

from . import config


def conectar():
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset="utf8mb4",
        cursorclass=DictCursor,
        autocommit=True,
        connect_timeout=5,
    )


def get_db():
    """Dependencia de FastAPI: una conexión por petición."""
    conn = conectar()
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def transaccion(conn):
    """BEGIN ... COMMIT; si algo falla dentro del bloque hace ROLLBACK y relanza el error."""
    conn.begin()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise


def uno(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchone()


def todos(conn, sql, params=()):
    with conn.cursor() as cur:
        cur.execute(sql, params)
        return cur.fetchall()


def ejecutar(conn, sql, params=()):
    """Ejecuta INSERT/UPDATE/DELETE. Devuelve (lastrowid, filas_afectadas)."""
    with conn.cursor() as cur:
        filas = cur.execute(sql, params)
        return cur.lastrowid, filas


def valor(conn, sql, params=()):
    fila = uno(conn, sql, params)
    return next(iter(fila.values())) if fila else None
