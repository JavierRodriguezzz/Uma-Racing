"""Toma capturas del sistema real (Chrome headless vía CDP) para la documentación.
Uso: python capturas.py <base_url> <carpeta_salida>
"""
import asyncio
import base64
import json
import subprocess
import sys
import tempfile
import time
import urllib.request

import websockets

BASE = sys.argv[1].rstrip("/")
SALIDA = sys.argv[2]
SOLO = set(sys.argv[3].split(",")) if len(sys.argv) > 3 else None
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PUERTO = 9334

perfil = tempfile.mkdtemp(prefix="uma-doc-")
proc = subprocess.Popen([CHROME, "--headless=new", f"--remote-debugging-port={PUERTO}", f"--user-data-dir={perfil}",
                         "--no-first-run", "--hide-scrollbars", "--enable-unsafe-swiftshader", "--use-angle=swiftshader", "--autoplay-policy=no-user-gesture-required",
                         "--window-size=1366,800", "about:blank"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def login(usuario, password):
    req = urllib.request.Request(f"{BASE}/api/auth/login", method="POST",
                                 data=json.dumps({"usuario": usuario, "password": password}).encode(),
                                 headers={"Content-Type": "application/json"})
    r = json.load(urllib.request.urlopen(req))
    return {"token": r["token"], "expira_en": r["expira_en"], "usuario": r["usuario"]}


# (nombre, ruta, sesión, ancho, alto, espera_s, página_completa, js_previo)
CAPTURAS = [
    ("login", "/login.html", None, 1366, 800, 2, False, None),
    ("login_error", "/login.html", None, 1366, 800, 2, False,
     "document.querySelector('input[name=usuario],#usuario').value='jugador1';"
     "document.querySelector('input[type=password]').value='incorrecta';"
     "document.querySelector('form').requestSubmit();"),
    ("registro_validacion", "/registro.html", None, 1366, 800, 2, False,
     "document.querySelector('form').requestSubmit();"),
    ("j_dashboard", "/dashboard.html", "jugador1", 1366, 800, 3, False, None),
    ("j_tienda", "/tienda.html", "jugador2", 1366, 800, 3, False, None),
    ("j_monedas", "/monedas.html", "jugador2", 1366, 800, 4, False, None),
    ("j_anuncios", "/anuncios.html", "jugador2", 1366, 800, 3, False, None),
    ("j_apuestas", "/apuestas.html", "jugador2", 1366, 800, 4, False, None),
    ("j_gacha", "/gacha.html", "jugador2", 1366, 800, 3, False, None),
    ("j_ranking", "/ranking.html", "jugador1", 1366, 800, 3, False, None),
    ("j_logros", "/logros.html", "jugador1", 1366, 800, 3, False, None),
    ("j_historial", "/historial.html", "jugador1", 1366, 800, 3, False, None),
    ("j_perfil", "/perfil.html", "jugador1", 1366, 800, 3, False, None),
    ("j_jugar", "/jugar.html", "jugador1", 1366, 800, 40, False, None),
    ("j_dormitorio", "/jugar.html#dormitorio", "jugador1", 1366, 800, 40, False, None),
    ("d_dormitorio", "/dormitorio.html", "jugador1", 1366, 800, 40, False, None),
    ("a_dashboard", "/dashboard.html", "admin", 1366, 800, 3, True, None),
    ("a_usuarios", "/admin/usuarios.html", "admin", 1366, 800, 3, False, None),
    ("a_items", "/admin/items.html", "admin", 1366, 800, 3, False, None),
    ("a_anuncios", "/admin/anuncios.html", "admin", 1366, 800, 3, False, None),
    ("a_logros", "/admin/logros.html", "admin", 1366, 800, 3, False, None),
    ("a_ventas", "/admin/ventas.html", "admin", 1366, 800, 3, False, None),
    ("a_paquetes", "/admin/paquetes.html", "admin", 1366, 800, 3, False, None),
    ("a_gacha", "/admin/gacha.html", "admin", 1366, 800, 3, False, None),
    ("a_reportes", "/admin/reportes.html", "admin", 1366, 800, 4, True, None),
    ("a_bitacora", "/admin/bitacora.html", "admin", 1366, 800, 3, False, None),
    ("swagger", "/docs", None, 1366, 800, 4, False, None),
    ("m_dashboard", "/dashboard.html", "jugador1", 390, 844, 3, False, None),
    ("m_tienda", "/tienda.html", "jugador2", 390, 844, 3, False, None),
    ("t_reportes", "/admin/reportes.html", "admin", 820, 1180, 4, False, None),
]


async def main():
    for _ in range(50):
        try:
            tabs = json.load(urllib.request.urlopen(f"http://127.0.0.1:{PUERTO}/json"))
            break
        except Exception:
            time.sleep(0.2)
    ws_url = next(t["webSocketDebuggerUrl"] for t in tabs if t["type"] == "page")
    sesiones = {u: login(u, p) for u, p in
                (("admin", "Admin123!"), ("jugador1", "Jugador123!"), ("jugador2", "Jugador123!"))}
    async with websockets.connect(ws_url, max_size=200_000_000) as ws:
        n = 0
        pendientes = {}

        async def cmd(metodo, **params):
            nonlocal n
            n += 1
            fut = asyncio.get_event_loop().create_future()
            pendientes[n] = fut
            await ws.send(json.dumps({"id": n, "method": metodo, "params": params}))
            return await fut

        async def lector():
            async for m in ws:
                d = json.loads(m)
                if "id" in d and d["id"] in pendientes:
                    pendientes.pop(d["id"]).set_result(d.get("result", d.get("error")))

        asyncio.create_task(lector())
        await cmd("Page.enable")
        await cmd("Runtime.enable")
        await cmd("Page.navigate", url=BASE + "/login.html")
        await asyncio.sleep(1.5)
        for nombre, ruta, usuario, ancho, alto, espera, completa, js in CAPTURAS:
            if SOLO and nombre not in SOLO:
                continue
            movil = ancho < 600
            await cmd("Emulation.setDeviceMetricsOverride", width=ancho, height=alto, deviceScaleFactor=2 if movil else 1.5,
                      mobile=movil)
            valor = json.dumps(json.dumps(sesiones[usuario])) if usuario else None
            expr = (f"localStorage.setItem('uma.sesion', {valor});" if valor else "localStorage.removeItem('uma.sesion');")
            await cmd("Runtime.evaluate", expression=expr)
            await cmd("Page.navigate", url=BASE + ruta)
            await asyncio.sleep(espera)
            if js:
                await cmd("Runtime.evaluate", expression=js)
                await asyncio.sleep(1.5)
            params = {"format": "png"}
            if completa:
                m = await cmd("Page.getLayoutMetrics")
                h = min(int(m["cssContentSize"]["height"]), 3200)
                params["clip"] = {"x": 0, "y": 0, "width": ancho, "height": h, "scale": 1}
                params["captureBeyondViewport"] = True
            r = await cmd("Page.captureScreenshot", **params)
            with open(f"{SALIDA}/{nombre}.png", "wb") as f:
                f.write(base64.b64decode(r["data"]))
            print("ok", nombre, flush=True)


try:
    asyncio.run(main())
finally:
    proc.kill()
