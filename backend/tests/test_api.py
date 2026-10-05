"""Pruebas de la API contra una base de datos de pruebas (cargar schema.sql + seed.sql antes).

Ejecutar desde backend/:   python -m pytest -v
Cada ejecución crea usuarios nuevos, por lo que puede repetirse sin recargar la BD.
"""
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app

c = TestClient(app, raise_server_exceptions=False)


def login(usuario, password):
    r = c.post("/api/auth/login", json={"usuario": usuario, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}


@pytest.fixture(scope="module")
def admin():
    return login("admin", "Admin123!")


@pytest.fixture()
def jugador():
    """Jugador recién registrado: 100 monedas de bienvenida y solo los personajes gratuitos."""
    nombre = "t_" + uuid.uuid4().hex[:10]
    r = c.post("/api/auth/registro", json={"username": nombre, "email": f"{nombre}@example.com", "password": "Prueba123"})
    assert r.status_code == 201, r.text
    return login(nombre, "Prueba123")


def saldo(h):
    return c.get("/api/auth/me", headers=h).json()["monedas"]


def item_id(h, codigo):
    datos = c.get("/api/items", params={"q": codigo}, headers=h).json()["datos"]
    return next(i["id"] for i in datos if i["codigo"] == codigo)


# ---------------------------------------------------------------- Autenticación
def test_cp01_login_valido():
    r = c.post("/api/auth/login", json={"usuario": "jugador1", "password": "Jugador123!"})
    assert r.status_code == 200 and r.json()["usuario"]["rol"] == "jugador"


def test_cp02_login_invalido():
    r = c.post("/api/auth/login", json={"usuario": "jugador1", "password": "incorrecta"})
    assert r.status_code == 401 and "incorrectos" in r.json()["error"]["mensaje"]


def test_cp03_campos_obligatorios():
    r = c.post("/api/auth/registro", json={"username": "", "email": "no-es-correo", "password": "corta"})
    assert r.status_code == 422
    assert {"username", "email", "password"} <= set(r.json()["error"]["detalles"])


def test_cp04_registro_duplicado():
    r = c.post("/api/auth/registro", json={"username": "jugador1", "email": "otro@example.com", "password": "Prueba123"})
    assert r.status_code == 409


def test_cp05_ruta_protegida_sin_token():
    assert c.get("/api/perfil").status_code == 401


def test_cp06_logout_revoca_token(jugador):
    assert c.post("/api/auth/logout", headers=jugador).status_code == 200
    assert c.get("/api/perfil", headers=jugador).status_code == 401


def test_cp07_permisos_insuficientes(jugador):
    assert c.get("/api/usuarios", headers=jugador).status_code == 403
    assert c.delete("/api/usuarios/1", headers=jugador).status_code == 403
    assert c.post("/api/items", headers=jugador, json={}).status_code in (403, 422)


def test_cp08_registro_inexistente(admin):
    assert c.get("/api/items/999999", headers=admin).status_code == 404
    assert c.get("/api/compras/UMA-999999", headers=admin).status_code == 404


# ---------------------------------------------------------------- Tienda (transacción)
def test_cp09_compra_sin_saldo_bloqueada(jugador):
    r = c.post("/api/compras", headers=jugador, json={"item_id": item_id(jugador, "junglepocket")})  # 450 > 100
    assert r.status_code == 409 and "Saldo insuficiente" in r.json()["error"]["mensaje"]
    assert saldo(jugador) == 100  # nada cambió


def test_cp10_compra_exitosa_y_duplicada(jugador, admin):
    me = c.get("/api/auth/me", headers=jugador).json()
    c.patch(f"/api/usuarios/{me['id']}/monedas", headers=admin, json={"monto": 400, "motivo": "Prueba automatizada"})
    condor = item_id(jugador, "elcondorpasa")
    r = c.post("/api/compras", headers=jugador, json={"item_id": condor})
    assert r.status_code == 201, r.text
    assert r.json()["folio"].startswith("UMA-") and r.json()["saldo"] == 200
    assert c.get("/api/juego/config", headers=jugador).json()["personajes"]["elcondorpasa"]["desbloqueado"]
    assert c.post("/api/compras", headers=jugador, json={"item_id": condor}).status_code == 409


def test_cp11_item_gratuito_no_se_compra(jugador):
    r = c.post("/api/compras", headers=jugador, json={"item_id": item_id(jugador, "goldship")})
    assert r.status_code == 409


def test_cp12_reembolso_admin(jugador, admin):
    me = c.get("/api/auth/me", headers=jugador).json()
    c.patch(f"/api/usuarios/{me['id']}/monedas", headers=admin, json={"monto": 300, "motivo": "Prueba de reembolso"})
    folio = c.post("/api/compras", headers=jugador, json={"item_id": item_id(jugador, "elcondorpasa")}).json()["folio"]
    assert c.post(f"/api/compras/{folio}/reembolso", headers=jugador, json={"motivo": "quiero"}).status_code == 403
    r = c.post(f"/api/compras/{folio}/reembolso", headers=admin, json={"motivo": "Compra por error"})
    assert r.status_code == 200 and r.json()["estado"] == "reembolsada"
    assert saldo(jugador) == 400
    assert not c.get("/api/juego/config", headers=jugador).json()["personajes"]["elcondorpasa"]["desbloqueado"]
    assert c.post(f"/api/compras/{folio}/reembolso", headers=admin, json={"motivo": "Otra vez"}).status_code == 409


# ---------------------------------------------------------------- Partidas
def test_cp13_personaje_bloqueado_no_juega(jugador):
    r = c.post("/api/partidas", headers=jugador, json={"personaje_j1": "junglepocket", "personaje_j2": "goldship"})
    assert r.status_code == 403 and "bloqueado" in r.json()["error"]["mensaje"]


def test_cp14_partida_valida_otorga_monedas_y_logros(jugador):
    token = c.post("/api/partidas", headers=jugador,
                   json={"personaje_j1": "goldship", "personaje_j2": "oguricap"}).json()["token"]
    time.sleep(1.2)
    r = c.post(f"/api/partidas/{token}/finalizar", headers=jugador,
               json={"ganador": "J1", "duracion_ms": 3100, "pulsaciones_j1": 30, "pulsaciones_j2": 20})
    assert r.status_code == 200, r.text
    cuerpo = r.json()
    assert cuerpo["puntaje"] == 500 + (45000 - 3100) // 100
    assert cuerpo["monedas_ganadas"] == 20
    assert {l["codigo"] for l in cuerpo["logros_nuevos"]} >= {"primera_carrera", "primera_victoria"}
    assert c.post(f"/api/partidas/{token}/finalizar", headers=jugador,
                  json={"ganador": "J1", "duracion_ms": 3100, "pulsaciones_j1": 30, "pulsaciones_j2": 20}).status_code == 409


def test_cp15_resultado_imposible_rechazado(jugador):
    token = c.post("/api/partidas", headers=jugador,
                   json={"personaje_j1": "goldship", "personaje_j2": "oguricap"}).json()["token"]
    antes = saldo(jugador)
    # Dice que la carrera duró 60 s cuando en el servidor pasó menos de 1 s
    r = c.post(f"/api/partidas/{token}/finalizar", headers=jugador,
               json={"ganador": "J1", "duracion_ms": 60000, "pulsaciones_j1": 300, "pulsaciones_j2": 200})
    assert r.status_code == 422 and "rechazado" in r.json()["error"]["mensaje"]
    assert saldo(jugador) == antes
    hist = c.get("/api/partidas", headers=jugador, params={"estado": "invalida"}).json()
    assert hist["total"] == 1  # el intento queda registrado


# ---------------------------------------------------------------- Publicidad
def test_cp16_anuncio_validado_por_servidor(jugador, admin):
    anuncio = c.post("/api/anuncios", headers=admin, json={
        "titulo": "Anuncio de prueba", "anunciante": "QA", "duracion_seg": 5, "recompensa_monedas": 7}).json()
    v = c.post(f"/api/anuncios/{anuncio['id']}/ver", headers=jugador).json()
    r = c.post(f"/api/anuncios/visualizaciones/{v['token']}/completar", headers=jugador)
    assert r.status_code == 422 and "no se ha visto completo" in r.json()["error"]["mensaje"]
    time.sleep(5)
    r = c.post(f"/api/anuncios/visualizaciones/{v['token']}/completar", headers=jugador)
    assert r.status_code == 200 and r.json()["monedas_otorgadas"] == 7 and r.json()["saldo"] == 107
    assert c.post(f"/api/anuncios/visualizaciones/{v['token']}/completar", headers=jugador).status_code == 409
    c.delete(f"/api/anuncios/{anuncio['id']}", headers=admin)


# ---------------------------------------------------------------- Admin y reglas
def test_cp17_no_desactivar_ultimo_admin_ni_a_si_mismo(admin):
    me = c.get("/api/auth/me", headers=admin).json()
    r = c.patch(f"/api/usuarios/{me['id']}/estado", headers=admin, json={"activo": False})
    assert r.status_code == 409


def test_cp18_minimo_de_personajes_gratuitos(admin):
    gold = item_id(admin, "goldship")
    r = c.delete(f"/api/items/{gold}", headers=admin)
    assert r.status_code == 409 and "gratuito" in r.json()["error"]["mensaje"]


def test_cp19_rango_de_fechas_invalido(admin):
    r = c.get("/api/reportes/ventas", headers=admin, params={"desde": "2026-10-05", "hasta": "2026-09-01"})
    assert r.status_code == 422


def test_cp20_inyeccion_sql_en_busqueda(admin):
    r = c.get("/api/usuarios", headers=admin, params={"q": "' OR 1=1 -- "})
    assert r.status_code == 200 and r.json()["total"] == 0


def test_cp21_bitacora_registra_operaciones(admin):
    datos = c.get("/api/bitacora", headers=admin, params={"accion": "compra"}).json()
    assert datos["total"] > 0 and datos["datos"][0]["estado_nuevo"]
