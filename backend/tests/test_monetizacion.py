"""Pruebas de compras con Google Pay (TEST), tiempo de juego, apuestas y gachapón."""
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app.db import conectar, ejecutar, uno
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
    nombre = "m_" + uuid.uuid4().hex[:10]
    c.post("/api/auth/registro", json={"username": nombre, "email": f"{nombre}@example.com", "password": "Prueba123"})
    h = login(nombre, "Prueba123")
    h["_id"] = str(c.get("/api/auth/me", headers=h).json()["id"])
    return h


def hdr(h):
    return {"Authorization": h["Authorization"]}


def saldo(h):
    return c.get("/api/auth/me", headers=hdr(h)).json()["monedas"]


def dar_monedas(admin, h, monto):
    r = c.patch(f"/api/usuarios/{h['_id']}/monedas", headers=admin, json={"monto": monto, "motivo": "Prueba automatizada"})
    assert r.status_code == 200, r.text


def sql(consulta, params=()):
    conn = conectar()
    try:
        ejecutar(conn, consulta, params)
    finally:
        conn.close()


PAYMENT_DATA_TEST = {
    "apiVersion": 2, "apiVersionMinor": 0,
    "paymentMethodData": {"type": "CARD", "description": "Visa •••• 1111",
                          "info": {"cardNetwork": "VISA", "cardDetails": "1111"},
                          "tokenizationData": {"type": "PAYMENT_GATEWAY", "token": "examplePaymentMethodToken"}},
}


# ---------------------------------------------------------------- Google Pay
def test_cp22_compra_monedas_google_pay(jugador):
    orden = c.post("/api/pagos/ordenes", headers=hdr(jugador), json={"paquete_id": 2}).json()
    assert orden["estado"] == "pendiente" and orden["transaccion"]["totalPrice"] == "49.00"
    r = c.post(f"/api/pagos/ordenes/{orden['folio']}/confirmar", headers=hdr(jugador), json=PAYMENT_DATA_TEST)
    assert r.status_code == 200, r.text
    assert r.json()["estado"] == "pagada" and r.json()["saldo"] == 100 + 880
    # Idempotencia: la misma orden no se puede cobrar dos veces
    assert c.post(f"/api/pagos/ordenes/{orden['folio']}/confirmar", headers=hdr(jugador), json=PAYMENT_DATA_TEST).status_code == 409


def test_cp23_token_invalido_rechazado(jugador):
    folio = c.post("/api/pagos/ordenes", headers=hdr(jugador), json={"paquete_id": 1}).json()["folio"]
    malo = {**PAYMENT_DATA_TEST, "paymentMethodData": {"type": "CARD", "tokenizationData": {"type": "PAYMENT_GATEWAY", "token": ""}}}
    r = c.post(f"/api/pagos/ordenes/{folio}/confirmar", headers=hdr(jugador), json=malo)
    assert r.status_code == 422 and saldo(jugador) == 100


def test_cp24_orden_expirada(jugador):
    folio = c.post("/api/pagos/ordenes", headers=hdr(jugador), json={"paquete_id": 1}).json()["folio"]
    sql("UPDATE ordenes_pago SET expira_en = NOW() - INTERVAL 1 MINUTE WHERE folio = %s", (folio,))
    r = c.post(f"/api/pagos/ordenes/{folio}/confirmar", headers=hdr(jugador), json=PAYMENT_DATA_TEST)
    assert r.status_code == 409 and "expiró" in r.json()["error"]["mensaje"]
    assert saldo(jugador) == 100


def test_cp25_admin_no_compra_monedas(admin):
    assert c.post("/api/pagos/ordenes", headers=admin, json={"paquete_id": 1}).status_code == 403


# ---------------------------------------------------------------- Tiempo de juego
def test_cp26_tiempo_de_juego_activo(jugador):
    token = c.post("/api/tiempo-juego/sesiones", headers=hdr(jugador)).json()["token"]
    assert c.post(f"/api/tiempo-juego/sesiones/{token}/latido", headers=hdr(jugador), json={"interacciones": 30}).status_code == 429
    # Simula que pasó un minuto y que ya llevaba 4 min 50 s acumulados
    sql("UPDATE sesiones_juego SET ultimo_latido = NOW() - INTERVAL 60 SECOND, segundos_sin_pagar = 290 WHERE token = %s", (token,))
    r = c.post(f"/api/tiempo-juego/sesiones/{token}/latido", headers=hdr(jugador), json={"interacciones": 30}).json()
    assert r["monedas_ganadas"] == 5 and r["saldo"] == 105
    # Un minuto sin teclas no cuenta
    sql("UPDATE sesiones_juego SET ultimo_latido = NOW() - INTERVAL 60 SECOND WHERE token = %s", (token,))
    r = c.post(f"/api/tiempo-juego/sesiones/{token}/latido", headers=hdr(jugador), json={"interacciones": 0}).json()
    assert r["segundos_contados"] == 0 and r["monedas_ganadas"] == 0


# ---------------------------------------------------------------- Apuestas
def test_cp27_apuesta_carrera_simulada(jugador):
    info = c.get("/api/apuestas/carrera", headers=hdr(jugador)).json()
    elegida = info["corredoras"][0]
    r = c.post("/api/apuestas/carrera", headers=hdr(jugador), json={"item_id": elegida["id"], "monto": 50})
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["ganadora"] == d["carrera"]["orden"][0]
    assert d["pago"] == (int(50 * elegida["momio"]) if d["gano"] else 0)
    assert d["saldo"] == 100 - 50 + d["pago"]


def test_cp28_apuesta_fuera_de_limites(jugador):
    r = c.post("/api/apuestas/carrera", headers=hdr(jugador), json={"item_id": 1, "monto": 5})
    assert r.status_code == 422
    r = c.post("/api/apuestas/carrera", headers=hdr(jugador), json={"item_id": 1, "monto": 200})  # tiene 100
    assert r.status_code == 409 and saldo(jugador) == 100


def test_cp29_limite_de_perdida_diaria(jugador, admin):
    dar_monedas(admin, jugador, 2000)
    sql("INSERT INTO apuestas (folio, usuario_id, tipo, monto, item_id, momio, estado) VALUES (%s, %s, 'carrera', 1480, 1, 3, 'perdida')",
        ("T" + uuid.uuid4().hex[:20], jugador["_id"]))
    r = c.post("/api/apuestas/carrera", headers=hdr(jugador), json={"item_id": 1, "monto": 50})
    assert r.status_code == 429 and "responsable" in r.json()["error"]["mensaje"]


def test_cp30_reto_de_tiempo_ganado(jugador):
    r = c.post("/api/apuestas/tiempo", headers=hdr(jugador), json={"objetivo_s": 20, "monto": 40})
    assert r.status_code == 201, r.text
    momio = r.json()["momio"]
    assert c.post("/api/apuestas/tiempo", headers=hdr(jugador), json={"objetivo_s": 20, "monto": 40}).status_code == 409
    token = c.post("/api/partidas", headers=hdr(jugador), json={"personaje_j1": "goldship", "personaje_j2": "oguricap"}).json()["token"]
    time.sleep(1.2)
    fin = c.post(f"/api/partidas/{token}/finalizar", headers=hdr(jugador),
                 json={"ganador": "J1", "duracion_ms": 3100, "pulsaciones_j1": 30, "pulsaciones_j2": 20}).json()
    assert fin["reto_tiempo"]["gano"] and fin["reto_tiempo"]["pago"] == int(40 * momio)


def test_cp31_cancelar_reto_devuelve_monedas(jugador):
    folio = c.post("/api/apuestas/tiempo", headers=hdr(jugador), json={"objetivo_s": 15, "monto": 30}).json()["folio"]
    assert saldo(jugador) == 70
    assert c.delete(f"/api/apuestas/{folio}", headers=hdr(jugador)).status_code == 200
    assert saldo(jugador) == 100


# ---------------------------------------------------------------- Gachapón
def test_cp32_gacha_sin_saldo(jugador):
    r = c.post("/api/gacha/tiradas", headers=hdr(jugador), json={"cantidad": 10})
    assert r.status_code == 409 and saldo(jugador) == 100


def test_cp33_gacha_diez_tiradas(jugador, admin):
    dar_monedas(admin, jugador, 800)
    r = c.post("/api/gacha/tiradas", headers=hdr(jugador), json={"cantidad": 10})
    assert r.status_code == 201, r.text
    d = r.json()
    assert len(d["resultados"]) == 10 and d["costo"] == 900
    assert d["saldo"] == sum(x["monedas"] for x in d["resultados"])


def test_cp34_gacha_garantia_epica(jugador):
    sql("UPDATE perfiles SET tiradas_sin_epica = 29 WHERE usuario_id = %s", (jugador["_id"],))
    r = c.post("/api/gacha/tiradas", headers=hdr(jugador), json={"cantidad": 1}).json()
    assert r["resultados"][0]["rareza"] == "epica" and r["resultados"][0]["por_garantia"]
    assert r["sin_epica"] == 0
    conn = conectar()
    try:
        assert uno(conn, "SELECT COUNT(*) AS n FROM inventario_usuario WHERE usuario_id = %s AND origen = 'gacha'",
                   (jugador["_id"],))["n"] == 1
    finally:
        conn.close()


def test_cp35_probabilidades_publicas_suman_uno(jugador):
    info = c.get("/api/gacha", headers=hdr(jugador)).json()
    assert abs(sum(p["probabilidad"] for p in info["premios"]) - 1) < 0.001
