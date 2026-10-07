"""Configuración leída de variables de entorno (.env). Nunca se escriben credenciales en el código."""
import os
from pathlib import Path

from dotenv import load_dotenv

RAIZ_REPO = Path(__file__).resolve().parents[2]
load_dotenv(RAIZ_REPO / ".env")
load_dotenv(RAIZ_REPO / "backend" / ".env")


def _int(nombre, defecto):
    return int(os.getenv(nombre, defecto))


def _bool(nombre, defecto):
    return os.getenv(nombre, str(defecto)).strip().lower() in ("1", "true", "si", "yes")


DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = _int("DB_PORT", 3306)
DB_NAME = os.getenv("DB_NAME", "uma_racing")
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")

JWT_SECRET = os.getenv("JWT_SECRET", "")
JWT_ALGORITMO = "HS256"
JWT_EXPIRA_HORAS = _int("JWT_EXPIRA_HORAS", 8)

# Reglas de negocio configurables
MONEDAS_REGISTRO = _int("MONEDAS_REGISTRO", 100)
ANUNCIOS_MAX_DIA = _int("ANUNCIOS_MAX_DIA", 5)
PARTIDAS_RECOMPENSA_MAX_DIA = _int("PARTIDAS_RECOMPENSA_MAX_DIA", 30)

# Google Pay (modo TEST: no cobra; PRODUCTION requiere una pasarela de pago real)
GOOGLE_PAY_ENTORNO = os.getenv("GOOGLE_PAY_ENTORNO", "TEST").upper()
GOOGLE_PAY_COMERCIO = os.getenv("GOOGLE_PAY_COMERCIO", "UmaRacing Online")
GOOGLE_PAY_MERCHANT_ID = os.getenv("GOOGLE_PAY_MERCHANT_ID", "")
ORDEN_PAGO_MINUTOS = _int("ORDEN_PAGO_MINUTOS", 15)

# Tiempo de juego: monedas por cada bloque de minutos activos
TIEMPO_BLOQUE_SEG = _int("TIEMPO_BLOQUE_SEG", 300)
TIEMPO_MONEDAS_BLOQUE = _int("TIEMPO_MONEDAS_BLOQUE", 5)
TIEMPO_MONEDAS_MAX_DIA = _int("TIEMPO_MONEDAS_MAX_DIA", 60)

# Apuestas (juego responsable)
APUESTA_MIN = _int("APUESTA_MIN", 10)
APUESTA_MAX = _int("APUESTA_MAX", 500)
APUESTA_PERDIDA_MAX_DIA = _int("APUESTA_PERDIDA_MAX_DIA", 1500)

CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]

# En desarrollo FastAPI también sirve el frontend y el juego compilado.
# En Docker eso lo hace Nginx y esta opción va en false.
SERVIR_FRONTEND = _bool("SERVIR_FRONTEND", True)
FRONTEND_DIR = Path(os.getenv("FRONTEND_DIR", RAIZ_REPO / "frontend"))
JUEGO_WEB_DIR = Path(os.getenv("JUEGO_WEB_DIR", RAIZ_REPO / "game" / "build" / "web"))

if len(JWT_SECRET) < 32:
    raise RuntimeError("JWT_SECRET debe definirse en .env con al menos 32 caracteres.")
