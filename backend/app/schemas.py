"""Modelos de entrada de la API. Pydantic valida tipos, longitudes y rangos antes de llegar a la lógica."""
import re
from typing import Literal

from pydantic import BaseModel, EmailStr, Field, field_validator

USERNAME_RE = re.compile(r"^[A-Za-z0-9_.]{3,30}$")
COLOR_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")
CODIGO_RE = re.compile(r"^[a-z0-9_]{3,40}$")


def _password_segura(valor: str) -> str:
    if len(valor) < 8:
        raise ValueError("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r"[A-Za-z]", valor) or not re.search(r"\d", valor):
        raise ValueError("La contraseña debe incluir letras y números.")
    return valor


def _texto(valor: str) -> str:
    valor = (valor or "").strip()
    if "<" in valor or ">" in valor:
        raise ValueError("No se permiten los caracteres < y >.")
    return valor


class _Base(BaseModel):
    model_config = {"extra": "forbid", "str_strip_whitespace": True}


# ---------- Autenticación / perfil ----------
class RegistroIn(_Base):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(max_length=72)
    nombre_mostrar: str | None = Field(default=None, max_length=50)

    @field_validator("username")
    @classmethod
    def _usuario(cls, v):
        if not USERNAME_RE.match(v):
            raise ValueError("Solo letras, números, punto y guion bajo (3 a 30 caracteres).")
        return v

    @field_validator("password")
    @classmethod
    def validar_1(cls, v):
        return _password_segura(v)
    @field_validator("nombre_mostrar")
    @classmethod
    def validar_2(cls, v):
        return _texto(v) if v else v


class LoginIn(_Base):
    usuario: str = Field(min_length=3, max_length=120, description="Nombre de usuario o correo")
    password: str = Field(min_length=1, max_length=72)


class PerfilIn(_Base):
    nombre_mostrar: str = Field(min_length=2, max_length=50)
    biografia: str = Field(default="", max_length=255)
    personaje_favorito_id: int | None = Field(default=None, gt=0)

    @field_validator("nombre_mostrar", "biografia")
    @classmethod
    def validar_3(cls, v):
        return _texto(v)


class PasswordIn(_Base):
    actual: str = Field(min_length=1, max_length=72)
    nueva: str = Field(max_length=72)

    @field_validator("nueva")
    @classmethod
    def validar_4(cls, v):
        return _password_segura(v)


# ---------- Tienda ----------
TIPOS_ITEM = ("personaje", "escenario", "chibi", "mueble")


class ItemIn(_Base):
    tipo: Literal["personaje", "escenario", "chibi", "mueble"]
    codigo: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=2, max_length=60)
    descripcion: str = Field(default="", max_length=255)
    precio: int = Field(ge=0, le=100000)
    es_gratuito: bool = False
    solo_gacha: bool = False          # no se vende con monedas: solo sale en el gachapón
    imagen_url: str | None = Field(default=None, max_length=255)
    activo: bool = True

    @field_validator("codigo")
    @classmethod
    def _codigo(cls, v):
        if not CODIGO_RE.match(v):
            raise ValueError("Usa minúsculas, números y guion bajo (3 a 40 caracteres).")
        return v

    @field_validator("nombre", "descripcion")
    @classmethod
    def validar_5(cls, v):
        return _texto(v)


class EstadoIn(_Base):
    activo: bool


class CompraIn(_Base):
    item_id: int = Field(gt=0)


class ReembolsoIn(_Base):
    motivo: str = Field(min_length=5, max_length=255)

    @field_validator("motivo")
    @classmethod
    def validar_6(cls, v):
        return _texto(v)


class EquiparIn(_Base):
    item_id: int = Field(gt=0)


# ---------- Anuncios ----------
class AnuncioIn(_Base):
    titulo: str = Field(min_length=3, max_length=80)
    anunciante: str = Field(min_length=2, max_length=80)
    descripcion: str = Field(default="", max_length=255)
    color: str = Field(default="#3b82f6")
    duracion_seg: int = Field(ge=5, le=120)
    recompensa_monedas: int = Field(ge=1, le=500)
    activo: bool = True

    @field_validator("color")
    @classmethod
    def _color(cls, v):
        if not COLOR_RE.match(v):
            raise ValueError("Color hexadecimal inválido (ej. #3b82f6).")
        return v

    @field_validator("titulo", "anunciante", "descripcion")
    @classmethod
    def validar_7(cls, v):
        return _texto(v)


# ---------- Partidas ----------
class PartidaInicioIn(_Base):
    personaje_j1: str = Field(min_length=3, max_length=40)
    personaje_j2: str = Field(min_length=3, max_length=40)
    escenario: str = Field(default="clasico", min_length=3, max_length=40)


class PartidaFinIn(_Base):
    ganador: Literal["J1", "J2"]
    duracion_ms: int = Field(gt=0, le=3_600_000)
    pulsaciones_j1: int = Field(ge=0, le=100_000)
    pulsaciones_j2: int = Field(ge=0, le=100_000)


# ---------- Logros ----------
class LogroIn(_Base):
    codigo: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=3, max_length=60)
    descripcion: str = Field(min_length=3, max_length=255)
    condicion: Literal["partidas_jugadas", "victorias", "anuncios_vistos", "compras", "puntaje_partida"]
    valor_objetivo: int = Field(gt=0, le=1_000_000)
    recompensa_monedas: int = Field(ge=0, le=5000)
    activo: bool = True

    @field_validator("codigo")
    @classmethod
    def _codigo(cls, v):
        if not CODIGO_RE.match(v):
            raise ValueError("Usa minúsculas, números y guion bajo (3 a 40 caracteres).")
        return v

    @field_validator("nombre", "descripcion")
    @classmethod
    def validar_8(cls, v):
        return _texto(v)


# ---------- Usuarios (administración) ----------
class UsuarioCrearIn(_Base):
    username: str = Field(min_length=3, max_length=30)
    email: EmailStr
    password: str = Field(max_length=72)
    nombre_mostrar: str = Field(min_length=2, max_length=50)
    rol: Literal["administrador", "jugador"] = "jugador"

    @field_validator("username")
    @classmethod
    def _usuario(cls, v):
        if not USERNAME_RE.match(v):
            raise ValueError("Solo letras, números, punto y guion bajo (3 a 30 caracteres).")
        return v

    @field_validator("password")
    @classmethod
    def validar_9(cls, v):
        return _password_segura(v)
    @field_validator("nombre_mostrar")
    @classmethod
    def validar_10(cls, v):
        return _texto(v)


class UsuarioEditarIn(_Base):
    email: EmailStr
    nombre_mostrar: str = Field(min_length=2, max_length=50)
    rol: Literal["administrador", "jugador"]

    @field_validator("nombre_mostrar")
    @classmethod
    def validar_11(cls, v):
        return _texto(v)


class AjusteMonedasIn(_Base):
    monto: int = Field(ge=-100_000, le=100_000)
    motivo: str = Field(min_length=5, max_length=200)

    @field_validator("monto")
    @classmethod
    def _no_cero(cls, v):
        if v == 0:
            raise ValueError("El monto no puede ser 0.")
        return v

    @field_validator("motivo")
    @classmethod
    def validar_12(cls, v):
        return _texto(v)


# ---------- Monedas con dinero (Google Pay) ----------
class PaqueteIn(_Base):
    nombre: str = Field(min_length=3, max_length=60)
    monedas: int = Field(ge=1, le=1_000_000)
    bonus: int = Field(ge=0, le=1_000_000)
    precio_mxn: float = Field(gt=0, le=10000)
    destacado: bool = False
    activo: bool = True

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v):
        return _texto(v)

    @field_validator("precio_mxn")
    @classmethod
    def validar_precio(cls, v):
        return round(v, 2)


class OrdenIn(_Base):
    paquete_id: int = Field(gt=0)


class GooglePayConfirmarIn(BaseModel):
    """Objeto PaymentData que devuelve Google Pay (se valida su estructura en el servidor)."""
    model_config = {"extra": "allow"}
    apiVersion: int
    apiVersionMinor: int
    paymentMethodData: dict


# ---------- Tiempo de juego ----------
class LatidoIn(_Base):
    interacciones: int = Field(ge=0, le=100_000)


# ---------- Apuestas ----------
class ApuestaCarreraIn(_Base):
    item_id: int = Field(gt=0)
    monto: int = Field(gt=0, le=100_000)


class ApuestaTiempoIn(_Base):
    objetivo_s: float = Field(ge=8, le=90)
    monto: int = Field(gt=0, le=100_000)


# ---------- Gachapón ----------
class TiradaIn(_Base):
    cantidad: Literal[1, 10]


# ---------- Dormitorio ----------
class PiezaIn(_Base):
    id: int = Field(gt=0)                 # pieza (fila de dormitorio_muebles)
    x: int = Field(ge=0, le=50)           # celda de la esquina superior izquierda
    z: int = Field(ge=0, le=50)
    rot: int = Field(ge=0, le=3)          # cuartos de vuelta


class AcomodoIn(_Base):
    """Piezas colocadas en el cuarto; las que no vienen aquí quedan guardadas en la bandeja."""
    piezas: list[PiezaIn] = Field(max_length=200)


class PremioIn(_Base):
    nombre: str = Field(min_length=3, max_length=60)
    rareza: Literal["comun", "rara", "epica"]
    tipo: Literal["item", "monedas"]
    item_id: int | None = Field(default=None, gt=0)
    monedas: int | None = Field(default=None, gt=0, le=100_000)
    peso: int = Field(ge=1, le=1000)
    monedas_repetido: int = Field(default=0, ge=0, le=100_000)
    activo: bool = True

    @field_validator("nombre")
    @classmethod
    def validar_nombre(cls, v):
        return _texto(v)
