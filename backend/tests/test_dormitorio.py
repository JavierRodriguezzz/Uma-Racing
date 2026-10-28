"""Pruebas del dormitorio: estado inicial, compras de chibis y muebles con monedas reales,
acomodo validado por el servidor, reembolsos y separación con la tienda del juego."""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import conectar, ejecutar
from app.main import app

c = TestClient(app, raise_server_exceptions=False)
INICIALES = ["alfombra_herradura", "cama_simple", "mesa_blanca", "sofa_menta", "tele_negra"]


def login(usuario, password):
    r = c.post("/api/auth/login", json={"usuario": usuario, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


def nuevo_jugador():
    nombre = "d_" + uuid.uuid4().hex[:10]
    c.post("/api/auth/registro", json={"username": nombre, "email": f"{nombre}@example.com", "password": "Prueba123"})
    h = login(nombre, "Prueba123")
    h["_id"] = str(c.get("/api/auth/me", headers=h).json()["id"])
    return h


@pytest.fixture(scope="module")
def admin():
    return login("admin", "Admin123!")


@pytest.fixture()
def jugador():
    return nuevo_jugador()


def hdr(h):
    return {"Authorization": h["Authorization"]}


def dar_monedas(admin, h, monto):
    r = c.patch(f"/api/usuarios/{h['_id']}/monedas", headers=admin, json={"monto": monto, "motivo": "Prueba automatizada"})
    assert r.status_code == 200, r.text


def estado(h):
    r = c.get("/api/dormitorio", headers=hdr(h))
    assert r.status_code == 200, r.text
    return r.json()


def item(est, codigo):
    return next(i for i in est["catalogo"] if i["codigo"] == codigo)


def comprar(h, item_id):
    return c.post("/api/compras", headers=hdr(h), json={"item_id": item_id})


def acomodar(h, piezas):
    return c.put("/api/dormitorio/acomodo", headers=hdr(h), json={"piezas": piezas})


def colocadas(est):
    return [{"id": m["id"], "x": m["x"], "z": m["z"], "rot": m["rot"]} for m in est["muebles"] if m["x"] is not None]


def pieza(est, codigo):
    return next(m for m in est["muebles"] if m["codigo"] == codigo)


def test_cp36_dormitorio_inicial(jugador):
    e = estado(jugador)
    assert e["monedas"] == 100 and e["chibis"] == [] and e["cuarto"] == {"ancho": 12, "fondo": 9}
    assert sorted(m["codigo"] for m in e["muebles"]) == INICIALES
    assert all(m["x"] is not None for m in e["muebles"])          # ya vienen acomodados
    assert len(estado(jugador)["muebles"]) == 5                    # abrirlo otra vez no los duplica
    assert {i["tipo"] for i in e["catalogo"]} == {"chibi", "mueble"}
    suzuka = item(e, "chibi_silencesuzuka")
    assert suzuka["solo_gacha"] and suzuka["en_gacha"] and suzuka["precio"] == 0
    assert item(e, "alfombra_pista")["pisable"] and (item(e, "cama_simple")["ancho"], item(e, "cama_simple")["fondo"]) == (2, 3)


def test_cp37_muebles_repetidos_y_saldo(jugador):
    e = estado(jugador)
    planta = item(e, "planta")["id"]
    r1 = comprar(jugador, planta)
    assert r1.status_code == 201, r1.text
    assert r1.json()["saldo"] == 60 and r1.json()["pieza_id"] and r1.json()["folio"].startswith("UMA-")
    r2 = comprar(jugador, planta)                                  # un mueble se puede tener varias veces
    # 2.ª compra: logro "Coleccionista" (+100), igual que en la tienda del juego
    assert r2.status_code == 201 and r2.json()["saldo"] == 20 + 100
    assert [l["codigo"] for l in r2.json()["logros_nuevos"]] == ["coleccionista"]
    plantas = [m for m in estado(jugador)["muebles"] if m["codigo"] == "planta"]
    assert len(plantas) == 2 and all(m["x"] is None for m in plantas)   # quedan guardadas en la bandeja
    r = comprar(jugador, item(e, "cama_ficha")["id"])
    assert r.status_code == 409 and estado(jugador)["monedas"] == 120   # saldo insuficiente: nada cambia
    assert comprar(jugador, item(e, "sofa_menta")["id"]).status_code == 409   # los gratuitos no se compran


def test_cp38_chibis(jugador, admin):
    dar_monedas(admin, jugador, 1000)
    e = estado(jugador)
    assert comprar(jugador, item(e, "chibi_fenomeno")["id"]).status_code == 201
    assert estado(jugador)["chibis"] == ["chibi_fenomeno"]
    assert comprar(jugador, item(e, "chibi_fenomeno")["id"]).status_code == 409   # una de cada una
    r = comprar(jugador, item(e, "chibi_silencesuzuka")["id"])
    assert r.status_code == 409 and "gachapón" in r.json()["error"]["mensaje"]   # exclusiva del gachapón
    assert estado(jugador)["monedas"] == 1100 - 250
    # La que sale en el gachapón entra al inventario y se muda al dormitorio
    conn = conectar()
    try:
        ejecutar(conn, "INSERT INTO inventario_usuario (usuario_id, item_id, origen) VALUES (%s, %s, 'gacha')",
                 (int(jugador["_id"]), item(e, "chibi_silencesuzuka")["id"]))
    finally:
        conn.close()
    assert set(estado(jugador)["chibis"]) == {"chibi_fenomeno", "chibi_silencesuzuka"}


def test_cp39_acomodo_valido(jugador):
    e = estado(jugador)
    pid = comprar(jugador, item(e, "planta")["id"]).json()["pieza_id"]
    cama = pieza(e, "cama_simple")["id"]
    # La cama se guarda (no viene en la lista) y la planta va a la esquina
    piezas = [p for p in colocadas(e) if p["id"] != cama] + [{"id": pid, "x": 11, "z": 8, "rot": 0}]
    r = acomodar(jugador, piezas)
    assert r.status_code == 200 and r.json()["colocadas"] == len(piezas)
    pos = {m["id"]: (m["x"], m["z"], m["rot"]) for m in estado(jugador)["muebles"]}
    assert pos[pid] == (11, 8, 0) and pos[cama] == (None, None, None)
    # Girada, la cama de 2×3 ocupa 3×2 y cabe abajo a la izquierda
    assert acomodar(jugador, piezas + [{"id": cama, "x": 0, "z": 7, "rot": 1}]).status_code == 200
    assert pieza(estado(jugador), "cama_simple")["rot"] == 1


def test_cp40_acomodo_invalido(jugador):
    e = estado(jugador)
    antes = {m["id"]: (m["x"], m["z"], m["rot"]) for m in e["muebles"]}
    base = colocadas(e)
    cama, tele = pieza(e, "cama_simple")["id"], pieza(e, "tele_negra")["id"]

    def con(pid, **cambio):
        return [{**p, **cambio} if p["id"] == pid else p for p in base]

    r = acomodar(jugador, con(cama, x=11))
    assert r.status_code == 422 and "fuera" in r.json()["error"]["mensaje"]
    r = acomodar(jugador, con(tele, x=0, z=0))                   # encima de la cama
    assert r.status_code == 422 and "encima" in r.json()["error"]["mensaje"]
    assert acomodar(jugador, base + [base[0]]).status_code == 422  # pieza repetida
    assert acomodar(jugador, con(cama, rot=4)).status_code == 422  # rotación inválida
    ajena = colocadas(estado(nuevo_jugador()))[0]
    assert acomodar(jugador, base + [ajena]).status_code == 404   # pieza de otro jugador
    assert acomodar(jugador, base).status_code == 200              # el acomodo inicial es válido (alfombra bajo la mesa)
    assert {m["id"]: (m["x"], m["z"], m["rot"]) for m in estado(jugador)["muebles"]} == antes


def test_cp41_reembolso_de_mueble(jugador, admin):
    e = estado(jugador)
    r = comprar(jugador, item(e, "planta")["id"]).json()
    rr = c.post(f"/api/compras/{r['folio']}/reembolso", headers=admin, json={"motivo": "Prueba de reembolso"})
    assert rr.status_code == 200, rr.text
    e = estado(jugador)
    assert r["pieza_id"] not in [m["id"] for m in e["muebles"]] and e["monedas"] == 100


def test_cp42_tienda_del_juego_y_permisos(jugador, admin):
    juego = c.get("/api/items", headers=hdr(jugador), params={"seccion": "juego", "limit": 100}).json()["datos"]
    assert {i["tipo"] for i in juego} == {"personaje", "escenario"}
    dorm = c.get("/api/items", headers=hdr(jugador), params={"seccion": "dormitorio", "limit": 100}).json()["datos"]
    assert {i["tipo"] for i in dorm} == {"chibi", "mueble"}
    assert c.get("/api/dormitorio", headers=admin).status_code == 403
    planta = item(estado(jugador), "planta")["id"]
    r = c.post("/api/gacha/premios", headers=admin,
               json={"nombre": "Planta de regalo", "rareza": "comun", "tipo": "item", "item_id": planta, "peso": 1})
    assert r.status_code == 422                                    # un mueble no puede ser premio
    inventario = c.get("/api/perfil/inventario", headers=hdr(jugador)).json()["datos"]
    assert inventario and all(i["tipo"] != "mueble" for i in inventario)
