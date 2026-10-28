"""UmaRacing Online — API REST (FastAPI).

Ejecutar en desarrollo:  uvicorn app.main:app --reload   (desde la carpeta backend/)
Documentación interactiva: http://localhost:8000/docs
"""
import logging
import threading

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from . import config
from .db import conectar, valor
from .errors import registrar_manejadores
from .services import simulador
from .routers import (anuncios, apuestas, auth, compras, dormitorio, gacha, items, logros, monedas, panel, partidas,
                      perfil, ranking, tiempo, usuarios)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

app = FastAPI(
    title="UmaRacing Online API",
    version="1.0.0",
    description="API del videojuego UmaRacing: usuarios, tienda con monedas virtuales, publicidad simulada, "
                "partidas, ranking, logros, reportes y bitácora. Autenticación con token Bearer (JWT).",
)

if config.CORS_ORIGINS:
    app.add_middleware(CORSMiddleware, allow_origins=config.CORS_ORIGINS, allow_credentials=False,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"], allow_headers=["Authorization", "Content-Type"])


@app.middleware("http")
async def cabeceras_seguridad(request, call_next):
    respuesta = await call_next(request)
    respuesta.headers.setdefault("X-Content-Type-Options", "nosniff")
    respuesta.headers.setdefault("Referrer-Policy", "same-origin")
    if request.url.path.startswith("/api/"):
        respuesta.headers["Cache-Control"] = "no-store"
    else:  # archivos estáticos: el navegador revalida (ETag) para no usar versiones viejas
        respuesta.headers.setdefault("Cache-Control", "no-cache")
    return respuesta


@app.on_event("startup")
def precalcular_momios():
    """Los momios salen de 4,000 simulaciones: se calculan al arrancar para que la primera visita sea inmediata."""
    def tarea():
        try:
            conn = conectar()
            try:
                simulador.momios(apuestas.corredoras(conn))
            finally:
                conn.close()
        except Exception:  # sin BD al arrancar: se calcularán en la primera petición
            logging.getLogger("uma.api").warning("No se pudieron precalcular los momios.")
    threading.Thread(target=tarea, daemon=True).start()


registrar_manejadores(app)
for r in (auth, perfil, items, compras, anuncios, partidas, ranking, logros, usuarios, panel,
          monedas, tiempo, apuestas, gacha, dormitorio):
    app.include_router(r.router)


@app.get("/api/salud", tags=["Sistema"], summary="Estado de la API y de la base de datos")
def salud():
    conn = conectar()
    try:
        return {"api": "ok", "base_de_datos": "ok" if valor(conn, "SELECT 1") == 1 else "error"}
    finally:
        conn.close()


# En desarrollo la misma app sirve el frontend y el juego compilado (en Docker lo hace Nginx)
if config.SERVIR_FRONTEND:
    # pygbag, cuando corre en localhost, pide sus paquetes (pygame para WebAssembly) a /cdn/
    # del mismo origen. Aquí se redirigen al CDN público de pygame-web.
    @app.get("/cdn/{ruta:path}", include_in_schema=False)
    def cdn_pygbag(ruta: str):
        return RedirectResponse(f"https://pygame-web.github.io/cdn/{ruta}")

    if config.JUEGO_WEB_DIR.exists():
        app.mount("/juego", StaticFiles(directory=config.JUEGO_WEB_DIR, html=True), name="juego")
    if config.FRONTEND_DIR.exists():
        app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
else:
    @app.get("/", include_in_schema=False)
    def raiz():
        return RedirectResponse("/docs")
