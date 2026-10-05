"""Evaluación automática de logros. Se llama dentro de la transacción de la operación que los dispara."""
from ..db import ejecutar, todos, uno
from . import bitacora, monedas


def progreso(conn, usuario_id) -> dict:
    """Valor actual de cada condición de logro para el usuario."""
    fila = uno(conn, """
        SELECT
          (SELECT COUNT(*) FROM partidas WHERE usuario_id = %(u)s AND estado = 'finalizada') AS partidas_jugadas,
          (SELECT COUNT(*) FROM partidas WHERE usuario_id = %(u)s AND estado = 'finalizada' AND ganador = 'J1') AS victorias,
          (SELECT COUNT(*) FROM visualizaciones_anuncio WHERE usuario_id = %(u)s AND estado = 'completada') AS anuncios_vistos,
          (SELECT COUNT(*) FROM compras WHERE usuario_id = %(u)s AND estado = 'completada') AS compras,
          (SELECT COALESCE(MAX(puntaje), 0) FROM partidas WHERE usuario_id = %(u)s AND estado = 'finalizada') AS puntaje_partida
    """, {"u": usuario_id})
    return {k: int(v) for k, v in fila.items()}


def evaluar(conn, usuario_id) -> list:
    """Otorga los logros activos cuya meta ya se cumplió y paga su recompensa. Devuelve los nuevos."""
    pendientes = todos(conn, """
        SELECT l.id, l.codigo, l.nombre, l.condicion, l.valor_objetivo, l.recompensa_monedas
        FROM logros l
        LEFT JOIN usuario_logros ul ON ul.logro_id = l.id AND ul.usuario_id = %s
        WHERE l.activo = 1 AND ul.logro_id IS NULL
    """, (usuario_id,))
    if not pendientes:
        return []
    actual = progreso(conn, usuario_id)
    nuevos = []
    for logro in pendientes:
        if actual[logro["condicion"]] >= logro["valor_objetivo"]:
            ejecutar(conn, "INSERT INTO usuario_logros (usuario_id, logro_id) VALUES (%s, %s)",
                     (usuario_id, logro["id"]))
            if logro["recompensa_monedas"]:
                monedas.mover(conn, usuario_id, "logro", logro["recompensa_monedas"],
                              f"Logro obtenido: {logro['nombre']}", logro["codigo"])
            bitacora.registrar(conn, usuario_id, "logro_obtenido", "logros", logro["id"],
                               nuevo=f"logro={logro['codigo']}")
            nuevos.append({"codigo": logro["codigo"], "nombre": logro["nombre"],
                           "recompensa_monedas": logro["recompensa_monedas"]})
    return nuevos
