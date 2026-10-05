"""Utilidades para listados: paginación, ordenamiento seguro y rangos de fechas."""
from datetime import date, timedelta
from math import ceil

from ..db import todos, valor
from ..errors import invalido


class Filtros:
    """Acumula condiciones WHERE con sus parámetros, sin concatenar valores del usuario."""

    def __init__(self):
        self.condiciones = []
        self.params = []

    def agregar(self, condicion, *params):
        self.condiciones.append(condicion)
        self.params.extend(params)
        return self

    def si(self, valor_param, condicion, *params):
        if valor_param is not None and valor_param != "":
            self.agregar(condicion, *(params or (valor_param,)))
        return self

    def buscar(self, texto, *columnas):
        if texto:
            patron = f"%{texto.strip()}%"
            self.agregar("(" + " OR ".join(f"{c} LIKE %s" for c in columnas) + ")", *([patron] * len(columnas)))
        return self

    def rango_fechas(self, columna, desde: date | None, hasta: date | None):
        if desde and hasta and desde > hasta:
            raise invalido("La fecha inicial no puede ser posterior a la fecha final.",
                           {"desde": "Debe ser menor o igual a la fecha final."})
        if desde:
            self.agregar(f"{columna} >= %s", desde)
        if hasta:
            self.agregar(f"{columna} < %s", hasta + timedelta(days=1))
        return self

    @property
    def where(self):
        return ("WHERE " + " AND ".join(self.condiciones)) if self.condiciones else ""


def orden_sql(orden: str | None, permitidos: dict, defecto: str) -> str:
    """Traduce `campo` o `-campo` a ORDER BY usando solo columnas de una lista blanca."""
    orden = orden or defecto
    desc = orden.startswith("-")
    clave = orden.lstrip("-")
    if clave not in permitidos:
        raise invalido("Campo de ordenamiento no permitido.",
                       {"orden": "Opciones: " + ", ".join(sorted(permitidos))})
    return f"ORDER BY {permitidos[clave]} {'DESC' if desc else 'ASC'}"


def paginar(conn, select_sql, from_sql, filtros: Filtros, orden: str, page: int, limit: int, mapear=None):
    """Ejecuta COUNT + SELECT paginado y devuelve el formato estándar de la API."""
    total = valor(conn, f"SELECT COUNT(*) AS n {from_sql} {filtros.where}", filtros.params) or 0
    filas = todos(conn, f"{select_sql} {from_sql} {filtros.where} {orden} LIMIT %s OFFSET %s",
                  [*filtros.params, limit, (page - 1) * limit])
    return {
        "pagina": page,
        "limite": limit,
        "total": total,
        "totalPaginas": max(1, ceil(total / limit)),
        "datos": [mapear(f) for f in filas] if mapear else filas,
    }
