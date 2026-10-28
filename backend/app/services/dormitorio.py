"""Dormitorio de cada jugador: sus chibis, sus muebles y dónde está cada uno.

- Las chibis van en inventario_usuario, como cualquier artículo (una de cada una).
- Cada mueble es una pieza en dormitorio_muebles: se pueden tener varias del mismo artículo.
  Con x, z y rot la pieza está colocada; sin posición está guardada en la bandeja.
- El servidor valida el acomodo con la huella de cada mueble (atributos_mueble) y el tamaño
  del cuarto, con las mismas reglas que frontend/js/dormitorio/main.js.
"""
from ..db import ejecutar, todos, transaccion, uno
from ..errors import invalido, no_encontrado

ANCHO, FONDO = 12, 9   # celdas del cuarto (CUARTO en frontend/js/dormitorio/datos.js)

# Acomodo con el que empieza un dormitorio nuevo (código del mueble gratuito → x, z, rot).
# Un mueble gratuito que no esté aquí se entrega guardado en la bandeja.
ACOMODO_INICIAL = {
    "cama_simple": (0, 0, 0),
    "alfombra_herradura": (5, 1, 0),
    "mesa_blanca": (5, 1, 0),        # sobre la alfombra: las alfombras solo chocan con alfombras
    "tele_negra": (5, 0, 0),
    "sofa_menta": (5, 4, 2),
}


def asegurar(conn, usuario_id):
    """Crea el dormitorio la primera vez que el jugador lo abre, con una pieza de cada mueble
    gratuito activo. Es idempotente: si ya existe no hace nada."""
    if uno(conn, "SELECT usuario_id FROM dormitorios WHERE usuario_id = %s", (usuario_id,)):
        return
    with transaccion(conn):
        _, creado = ejecutar(conn, "INSERT IGNORE INTO dormitorios (usuario_id) VALUES (%s)", (usuario_id,))
        if not creado:   # otra petición simultánea lo creó primero
            return
        gratuitos = todos(conn, "SELECT i.id, i.codigo FROM items i JOIN tipos_item t ON t.id = i.tipo_id "
                                "WHERE t.codigo = 'mueble' AND i.es_gratuito = 1 AND i.activo = 1 ORDER BY i.id")
        for m in gratuitos:
            x, z, rot = ACOMODO_INICIAL.get(m["codigo"], (None, None, None))
            ejecutar(conn, "INSERT INTO dormitorio_muebles (usuario_id, item_id, origen, x, z, rot) "
                           "VALUES (%s, %s, 'inicial', %s, %s, %s)", (usuario_id, m["id"], x, z, rot))


def estado(conn, usuario_id):
    """Todo lo que el dormitorio necesita para dibujarse: monedas, catálogo a la venta, chibis y piezas."""
    dorm = uno(conn, "SELECT d.nombre, p.monedas FROM dormitorios d JOIN perfiles p ON p.usuario_id = d.usuario_id "
                     "WHERE d.usuario_id = %s", (usuario_id,))
    if not dorm:
        raise no_encontrado("El dormitorio no existe.")
    catalogo = todos(conn, """
        SELECT i.id, t.codigo AS tipo, i.codigo, i.nombre, i.precio, i.es_gratuito, i.solo_gacha,
               am.ancho, am.fondo, am.pisable,
               EXISTS (SELECT 1 FROM gacha_premios g WHERE g.item_id = i.id AND g.activo = 1) AS en_gacha
        FROM items i
        JOIN tipos_item t ON t.id = i.tipo_id
        LEFT JOIN atributos_mueble am ON am.item_id = i.id
        WHERE t.codigo IN ('chibi', 'mueble') AND i.activo = 1
        ORDER BY t.id, i.precio, i.id
    """)
    for c in catalogo:
        for k in ("es_gratuito", "solo_gacha", "en_gacha"):
            c[k] = bool(c[k])
        c["pisable"] = None if c["pisable"] is None else bool(c["pisable"])
    chibis = todos(conn, """
        SELECT i.codigo FROM items i
        JOIN tipos_item t ON t.id = i.tipo_id
        LEFT JOIN inventario_usuario inv ON inv.item_id = i.id AND inv.usuario_id = %s
        WHERE t.codigo = 'chibi' AND (inv.id IS NOT NULL OR (i.es_gratuito = 1 AND i.activo = 1))
        ORDER BY COALESCE(inv.adquirido_en, i.creado_en), i.id
    """, (usuario_id,))
    muebles = todos(conn, "SELECT dm.id, i.codigo, dm.x, dm.z, dm.rot FROM dormitorio_muebles dm "
                          "JOIN items i ON i.id = dm.item_id WHERE dm.usuario_id = %s ORDER BY dm.id", (usuario_id,))
    return {"nombre": dorm["nombre"], "monedas": dorm["monedas"], "cuarto": {"ancho": ANCHO, "fondo": FONDO},
            "catalogo": catalogo, "chibis": [c["codigo"] for c in chibis], "muebles": muebles}


def guardar_acomodo(conn, usuario_id, piezas):
    """RN: cada pieza colocada debe ser del jugador, caber en el cuarto y no encimarse con otra
    (las alfombras solo chocan con alfombras). Las piezas que no vienen en la lista quedan guardadas."""
    ids = [p.id for p in piezas]
    if len(ids) != len(set(ids)):
        raise invalido("Una pieza aparece dos veces en el acomodo.")
    with transaccion(conn):
        mias = {r["id"]: r for r in todos(conn, """
            SELECT dm.id, i.nombre, am.ancho, am.fondo, am.pisable
            FROM dormitorio_muebles dm
            JOIN items i ON i.id = dm.item_id
            LEFT JOIN atributos_mueble am ON am.item_id = dm.item_id
            WHERE dm.usuario_id = %s FOR UPDATE
        """, (usuario_id,))}
        colocadas = []
        for p in piezas:
            m = mias.get(p.id)
            if not m:
                raise no_encontrado("Una de las piezas no existe o no es tuya.")
            if m["ancho"] is None:
                raise invalido(f"{m['nombre']} no se puede colocar en el cuarto.")
            w, d = (m["ancho"], m["fondo"]) if p.rot % 2 == 0 else (m["fondo"], m["ancho"])
            if p.x + w > ANCHO or p.z + d > FONDO:
                raise invalido(f"{m['nombre']} queda fuera del cuarto.")
            for o in colocadas:
                if o["pisable"] == m["pisable"] and p.x < o["x"] + o["w"] and o["x"] < p.x + w \
                        and p.z < o["z"] + o["d"] and o["z"] < p.z + d:
                    raise invalido(f"{m['nombre']} se encima con {o['nombre']}.")
            colocadas.append({"x": p.x, "z": p.z, "w": w, "d": d, "pisable": m["pisable"], "nombre": m["nombre"]})
        ejecutar(conn, "UPDATE dormitorio_muebles SET x = NULL, z = NULL, rot = NULL WHERE usuario_id = %s", (usuario_id,))
        for p in piezas:
            ejecutar(conn, "UPDATE dormitorio_muebles SET x = %s, z = %s, rot = %s WHERE id = %s AND usuario_id = %s",
                     (p.x, p.z, p.rot, p.id, usuario_id))
    return len(piezas)
