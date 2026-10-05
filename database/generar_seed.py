"""
Genera database/seed.sql con datos de prueba coherentes:
usuarios con contraseña bcrypt, partidas de los últimos 60 días, compras,
anuncios vistos, movimientos con saldo consistente y logros obtenidos.

Las fechas se escriben relativas a NOW() para que las gráficas
siempre muestren actividad reciente.

Uso:  python database/generar_seed.py   (requiere: pip install bcrypt)
"""
import random
import uuid
from pathlib import Path

import bcrypt

random.seed(2026)
SALIDA = Path(__file__).with_name("seed.sql")
DIAS = 60

# Reglas iguales a backend/app/services/reglas.py
MONEDAS_REGISTRO = 100
MONEDAS_VICTORIA = 20
MONEDAS_DERROTA = 5


def calcular_puntaje(ganador, duracion_ms):
    if ganador == "J1":
        return 500 + max(0, (45000 - duracion_ms) // 100)
    return 100


def q(valor):
    """Literal SQL seguro para los valores fijos de este script."""
    if valor is None:
        return "NULL"
    if isinstance(valor, (int, float)):
        return str(valor)
    return "'" + str(valor).replace("\\", "\\\\").replace("'", "''") + "'"


def hace(segundos):
    return f"NOW() - INTERVAL {int(segundos)} SECOND"


def hash_pw(texto):
    return bcrypt.hashpw(texto.encode(), bcrypt.gensalt(rounds=10)).decode()


ITEMS = [
    # id, tipo, codigo, nombre, descripcion, precio, gratuito, imagen
    (1, 1, "goldship", "Gold Ship", "Impredecible y caótica. Personaje inicial.", 0, 1, "img/personajes/goldship.png"),
    (2, 1, "oguricap", "Oguri Cap", "La glotona de corazón enorme. Personaje inicial.", 0, 1, "img/personajes/oguricap.png"),
    (3, 1, "elcondorpasa", "El Condor Pasa", "Luchadora enmascarada con estilo propio.", 300, 0, "img/personajes/elcondorpasa.png"),
    (4, 1, "junglepocket", "Jungle Pocket", "Rival feroz que nunca se rinde.", 450, 0, "img/personajes/junglepocket.png"),
    (5, 2, "clasico", "Pradera Clásica", "El escenario original de UmaRacing.", 0, 1, "img/escenarios/clasico.png"),
    (6, 2, "atardecer", "Atardecer", "Escenario de ejemplo: la pradera al caer el sol.", 250, 0, "img/escenarios/atardecer.png"),
]
PERSONAJES_GRATIS = [1, 2]
ESCENARIO_BASE = 5

ANUNCIOS = [
    (1, "Zanahorias Turbo", "Granja Galope S.A.", "La zanahoria crujiente de los campeones.", "#f97316", 10, 15),
    (2, "Bebida Sprint+", "Bebidas Meta", "Hidratación para la recta final.", "#06b6d4", 15, 25),
    (3, "Herraduras Pro", "Taller Trote", "Agarre perfecto en cualquier pista.", "#64748b", 8, 10),
    (4, "Academia Tracen", "Escuela Tracen", "Inscripciones abiertas para nuevas corredoras.", "#a855f7", 20, 40),
    (5, "Pista Arcoíris", "Parque Hipódromo", "Visita el parque temático más veloz.", "#22c55e", 12, 20),
]

LOGROS = [
    (1, "primera_carrera", "Primera carrera", "Completa tu primera partida.", "partidas_jugadas", 1, 20),
    (2, "corredor_10", "Corredor constante", "Completa 10 partidas.", "partidas_jugadas", 10, 50),
    (3, "maratonista_50", "Maratonista", "Completa 50 partidas.", "partidas_jugadas", 50, 200),
    (4, "primera_victoria", "Primera victoria", "Gana una partida como Jugador 1.", "victorias", 1, 25),
    (5, "campeon_25", "Campeón", "Gana 25 partidas como Jugador 1.", "victorias", 25, 150),
    (6, "patrocinado", "Patrocinado", "Mira 5 anuncios completos.", "anuncios_vistos", 5, 30),
    (7, "coleccionista", "Coleccionista", "Compra 2 artículos en la tienda.", "compras", 2, 100),
    (8, "velocista", "Velocista", "Obtén 800 puntos o más en una sola partida.", "puntaje_partida", 800, 75),
]

NOMBRES = [
    ("carlos_r", "Carlos R."), ("ana_speed", "Ana Speed"), ("luisito99", "Luisito"),
    ("valeria.m", "Vale M."), ("diego_turbo", "Diego Turbo"), ("sofia_uma", "Sofía"),
    ("pepe_gamer", "Pepe Gamer"), ("mariana_g", "Mariana G."), ("kevin_run", "Kevin Run"),
    ("fer_pista", "Fer Pista"), ("andrea_q", "Andrea Q."), ("rodo_meta", "Rodo Meta"),
]


def main():
    sql = []
    w = sql.append
    w("-- =====================================================================")
    w("--  UmaRacing Online — Datos de prueba (generado por generar_seed.py)")
    w("--  Ejecutar DESPUÉS de schema.sql:  mysql -u root -p uma_racing < database/seed.sql")
    w("-- =====================================================================")
    w("USE uma_racing;")
    w("SET NAMES utf8mb4;")
    w("")
    w("INSERT INTO roles (id, nombre, descripcion) VALUES")
    w("  (1, 'administrador', 'Gestiona tienda, anuncios, logros, usuarios y reportes.'),")
    w("  (2, 'jugador', 'Juega, compra en la tienda, mira anuncios y consulta su progreso.');")
    w("")
    w("INSERT INTO tipos_item (id, codigo, nombre) VALUES (1, 'personaje', 'Personaje'), (2, 'escenario', 'Escenario');")
    w("")
    w("INSERT INTO items (id, tipo_id, codigo, nombre, descripcion, precio, es_gratuito, imagen_url) VALUES")
    w(",\n".join(f"  ({i}, {t}, {q(c)}, {q(n)}, {q(d)}, {p}, {g}, {q(img)})" for i, t, c, n, d, p, g, img in ITEMS) + ";")
    w("")
    w("INSERT INTO anuncios (id, titulo, anunciante, descripcion, color, duracion_seg, recompensa_monedas) VALUES")
    w(",\n".join(f"  ({i}, {q(t)}, {q(a)}, {q(d)}, {q(c)}, {s}, {r})" for i, t, a, d, c, s, r in ANUNCIOS) + ";")
    w("")
    w("INSERT INTO logros (id, codigo, nombre, descripcion, condicion, valor_objetivo, recompensa_monedas) VALUES")
    w(",\n".join(f"  ({i}, {q(c)}, {q(n)}, {q(d)}, {q(k)}, {v}, {r})" for i, c, n, d, k, v, r in LOGROS) + ";")
    w("")

    # ---- Usuarios ----
    usuarios = [
        # id, rol, username, email, password, nombre, dias_antig, actividad
        (1, 1, "admin", "admin@example.com", "Admin123!", "Administrador", DIAS + 5, 0),
        (2, 2, "jugador1", "jugador1@example.com", "Jugador123!", "Jugador Uno", DIAS, 1.0),
        # Cuenta de demostración: sin compras, con Condor y Jungle bloqueados y saldo para comprar uno
        (3, 2, "jugador2", "jugador2@example.com", "Jugador123!", "Jugador Dos", 2, 0),
    ]
    pw_demo = hash_pw("Demo1234!")
    for k, (user, nombre) in enumerate(NOMBRES, start=4):
        usuarios.append((k, 2, user, f"{user.replace('.', '')}@example.com", None, nombre,
                         random.randint(20, DIAS), random.uniform(0.2, 0.9)))

    w("INSERT INTO usuarios (id, rol_id, username, email, password_hash, activo, creado_en, ultimo_acceso) VALUES")
    filas = []
    for uid, rol, user, email, pw, nombre, dias, _ in usuarios:
        h = hash_pw(pw) if pw else pw_demo
        activo = 0 if user == "rodo_meta" else 1
        filas.append(f"  ({uid}, {rol}, {q(user)}, {q(email)}, {q(h)}, {activo}, {hace(dias * 86400)}, {hace(random.randint(0, 3) * 86400 + 3600)})")
    w(",\n".join(filas) + ";")
    w("")

    # ---- Simulación de actividad por jugador ----
    perfiles, partidas, compras, inventario = [], [], [], []
    movimientos, visualizaciones, usuario_logros, bitacora = [], [], [], []
    partida_id = compra_id = vis_id = 0

    for uid, rol, user, email, pw, nombre, dias, actividad in usuarios:
        bitacora.append((uid, "registro", "usuarios", uid, None, f"usuario={user}", dias * 86400))
        if rol == 1:
            perfiles.append((uid, nombre, "Cuenta de administración.", 0, None, None))
            continue

        eventos = []  # (segundos_atras, tipo, datos)
        for d in range(dias, -1, -1):
            if random.random() < actividad:
                for _ in range(random.randint(1, 5)):
                    eventos.append((d * 86400 - random.randint(0, 80000), "partida", None))
            if random.random() < actividad * 0.4:
                eventos.append((d * 86400 - random.randint(0, 80000), "anuncio", random.choice(ANUNCIOS)))
        eventos = [e for e in eventos if e[0] > 60]
        eventos.sort(key=lambda e: -e[0])

        saldo = 0
        poseidos = set(PERSONAJES_GRATIS)
        escenarios = {ESCENARIO_BASE}
        cont = {"partidas_jugadas": 0, "victorias": 0, "anuncios_vistos": 0, "compras": 0, "puntaje_partida": 0}
        obtenidos = set()

        def mover(tipo, monto, ref, desc, seg):
            nonlocal saldo
            movimientos.append((uid, tipo, monto, saldo, saldo + monto, ref, desc, seg))
            saldo += monto

        def revisar_logros(seg):
            for lid, codigo, lnombre, _, cond, objetivo, recompensa in LOGROS:
                if lid not in obtenidos and cont[cond] >= objetivo:
                    obtenidos.add(lid)
                    usuario_logros.append((uid, lid, seg))
                    if recompensa:
                        mover("logro", recompensa, codigo, f"Logro obtenido: {lnombre}", seg)

        mover("registro", MONEDAS_REGISTRO, None, "Bono de bienvenida", dias * 86400)
        if actividad == 0:
            mover("ajuste", 250, None, "Ajuste del administrador: monedas para la demostración", dias * 86400 - 60)

        for seg, tipo, datos in eventos:
            if tipo == "partida":
                partida_id += 1
                pj1 = random.choice(sorted(poseidos))
                pj2 = random.choice(PERSONAJES_GRATIS + [p for p in poseidos if p not in PERSONAJES_GRATIS])
                esc = random.choice(sorted(escenarios))
                gana = "J1" if random.random() < 0.55 else "J2"
                dur = random.randint(11000, 32000)
                p1 = int(dur / 1000 * random.uniform(6, 9))
                p2 = int(dur / 1000 * random.uniform(5, 9))
                puntaje = calcular_puntaje(gana, dur)
                monedas = MONEDAS_VICTORIA if gana == "J1" else MONEDAS_DERROTA
                partidas.append((partida_id, uid, str(uuid.UUID(int=random.getrandbits(128))), pj1, pj2, esc,
                                 gana, dur, p1, p2, puntaje, monedas, seg))
                mover("partida", monedas, f"P-{partida_id}", f"Partida #{partida_id} ({'victoria' if gana == 'J1' else 'derrota'})", seg - dur // 1000)
                cont["partidas_jugadas"] += 1
                cont["victorias"] += gana == "J1"
                cont["puntaje_partida"] = max(cont["puntaje_partida"], puntaje)
                revisar_logros(seg - dur // 1000)
            else:
                aid, titulo, _, _, _, dur_ad, recompensa = datos
                vis_id += 1
                visualizaciones.append((vis_id, uid, aid, str(uuid.UUID(int=random.getrandbits(128))), recompensa, seg, dur_ad))
                mover("anuncio", recompensa, f"AD-{vis_id}", f"Recompensa por anuncio: {titulo}", seg - dur_ad)
                cont["anuncios_vistos"] += 1
                revisar_logros(seg - dur_ad)

            # Compra cuando alcanza el saldo (deseo aleatorio)
            for item in ITEMS:
                iid, _, codigo, inombre, _, precio, gratis, _ = item
                if gratis or iid in poseidos or iid in escenarios:
                    continue
                if saldo >= precio and random.random() < 0.25:
                    compra_id += 1
                    folio = f"UMA-{compra_id:06d}"
                    s2 = seg - 30
                    compras.append((compra_id, folio, uid, iid, precio, s2))
                    inventario.append((uid, iid, compra_id, s2))
                    mover("compra", -precio, folio, f"Compra de {inombre}", s2)
                    bitacora.append((uid, "compra", "compras", folio, None, f"item={codigo}; precio={precio}", s2))
                    (escenarios if item[1] == 2 else poseidos).add(iid)
                    cont["compras"] += 1
                    revisar_logros(s2)

        favorito = random.choice(sorted(poseidos))
        esc_eq = max(escenarios)
        perfiles.append((uid, nombre, "", saldo, favorito, esc_eq))

    # ---- Volcado ----
    w("INSERT INTO perfiles (usuario_id, nombre_mostrar, biografia, monedas, personaje_favorito_id, escenario_equipado_id) VALUES")
    w(",\n".join(f"  ({u}, {q(n)}, {q(b)}, {m}, {q(f)}, {q(e)})" for u, n, b, m, f, e in perfiles) + ";")
    w("")

    def bloques(cabecera, filas, tam=200):
        for i in range(0, len(filas), tam):
            w(cabecera)
            w(",\n".join(filas[i:i + tam]) + ";")
        w("")

    bloques("INSERT INTO compras (id, folio, usuario_id, item_id, precio_pagado, creada_en) VALUES",
            [f"  ({c}, {q(f)}, {u}, {i}, {p}, {hace(s)})" for c, f, u, i, p, s in compras])
    bloques("INSERT INTO inventario_usuario (usuario_id, item_id, compra_id, origen, adquirido_en) VALUES",
            [f"  ({u}, {i}, {c}, 'compra', {hace(s)})" for u, i, c, s in inventario])
    bloques("INSERT INTO partidas (id, usuario_id, token, personaje_j1_id, personaje_j2_id, escenario_id, estado, ganador, "
            "duracion_ms, pulsaciones_j1, pulsaciones_j2, puntaje, monedas_ganadas, iniciada_en, finalizada_en) VALUES",
            [f"  ({p}, {u}, {q(t)}, {a}, {b}, {e}, 'finalizada', {q(g)}, {d}, {x}, {y}, {pt}, {m}, {hace(s)}, {hace(s - d // 1000)})"
             for p, u, t, a, b, e, g, d, x, y, pt, m, s in partidas])
    bloques("INSERT INTO visualizaciones_anuncio (id, usuario_id, anuncio_id, token, estado, monedas_otorgadas, iniciada_en, completada_en) VALUES",
            [f"  ({v}, {u}, {a}, {q(t)}, 'completada', {r}, {hace(s)}, {hace(s - d)})" for v, u, a, t, r, s, d in visualizaciones])
    bloques("INSERT INTO movimientos_monedas (usuario_id, tipo, monto, saldo_anterior, saldo_nuevo, referencia, descripcion, creado_en) VALUES",
            [f"  ({u}, {q(t)}, {m}, {a}, {n}, {q(r)}, {q(d)}, {hace(s)})" for u, t, m, a, n, r, d, s in movimientos])
    bloques("INSERT INTO usuario_logros (usuario_id, logro_id, obtenido_en) VALUES",
            [f"  ({u}, {l}, {hace(s)})" for u, l, s in usuario_logros])
    bloques("INSERT INTO bitacora (usuario_id, accion, entidad, entidad_id, estado_anterior, estado_nuevo, creado_en) VALUES",
            [f"  ({u}, {q(a)}, {q(e)}, {q(i)}, {q(x)}, {q(y)}, {hace(s)})" for u, a, e, i, x, y, s in bitacora])

    SALIDA.write_text("\n".join(sql), encoding="utf-8")
    print(f"seed.sql generado: {len(usuarios)} usuarios, {len(partidas)} partidas, "
          f"{len(compras)} compras, {len(visualizaciones)} anuncios vistos, {len(movimientos)} movimientos")


if __name__ == "__main__":
    main()
