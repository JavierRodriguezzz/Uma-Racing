"""Monedero virtual. Debe llamarse SIEMPRE dentro de una transacción."""
from ..db import ejecutar, uno
from ..errors import conflicto, no_encontrado


def bloquear_saldo(conn, usuario_id) -> int:
    """SELECT ... FOR UPDATE: evita que dos operaciones simultáneas gasten el mismo saldo."""
    fila = uno(conn, "SELECT monedas FROM perfiles WHERE usuario_id = %s FOR UPDATE", (usuario_id,))
    if not fila:
        raise no_encontrado("El perfil del usuario no existe.")
    return fila["monedas"]


def mover(conn, usuario_id, tipo, monto, descripcion, referencia=None) -> int:
    """Suma o resta monedas y deja el movimiento en el libro mayor. Devuelve el saldo nuevo."""
    if monto == 0:
        return bloquear_saldo(conn, usuario_id)
    saldo = bloquear_saldo(conn, usuario_id)
    nuevo = saldo + monto
    if nuevo < 0:
        raise conflicto(f"Saldo insuficiente: tienes {saldo} monedas y se requieren {-monto}.")
    ejecutar(conn, "UPDATE perfiles SET monedas = %s WHERE usuario_id = %s", (nuevo, usuario_id))
    ejecutar(conn,
             "INSERT INTO movimientos_monedas (usuario_id, tipo, monto, saldo_anterior, saldo_nuevo, referencia, descripcion) "
             "VALUES (%s, %s, %s, %s, %s, %s, %s)",
             (usuario_id, tipo, monto, saldo, nuevo, referencia, descripcion[:255]))
    return nuevo
