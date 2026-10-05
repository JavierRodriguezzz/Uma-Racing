"""Reglas de negocio puras (sin BD) para que sean fáciles de leer, probar y documentar."""
MONEDAS_VICTORIA = 20
MONEDAS_DERROTA = 5

DURACION_MIN_MS = 3_000          # una carrera real no dura menos de 3 s
DURACION_MAX_MS = 600_000        # ni más de 10 min
PULSACIONES_MAX_POR_SEG = 20     # límite humano razonable al alternar teclas
TOLERANCIA_RELOJ_MS = 2_000      # diferencia aceptada entre el reloj del juego y el del servidor
VENTANA_ANUNCIO_MIN = 10         # minutos para reclamar un anuncio iniciado


def calcular_puntaje(ganador: str, duracion_ms: int) -> int:
    """RN: victoria = 500 + bono por rapidez; derrota = 100 de participación."""
    if ganador == "J1":
        return 500 + max(0, (45_000 - duracion_ms) // 100)
    return 100


def calcular_monedas_partida(ganador: str, partidas_premiadas_hoy: int, limite_diario: int) -> int:
    """RN: se premian como máximo `limite_diario` partidas por día para evitar farmeo."""
    if partidas_premiadas_hoy >= limite_diario:
        return 0
    return MONEDAS_VICTORIA if ganador == "J1" else MONEDAS_DERROTA


def validar_resultado_partida(duracion_ms, pulsaciones_j1, pulsaciones_j2, ms_servidor):
    """RN: el servidor rechaza resultados imposibles enviados por el cliente.
    Devuelve None si es válido o el motivo del rechazo."""
    if not DURACION_MIN_MS <= duracion_ms <= DURACION_MAX_MS:
        return "La duración de la carrera está fuera del rango permitido."
    if ms_servidor + TOLERANCIA_RELOJ_MS < duracion_ms:
        return "La duración reportada es mayor al tiempo real transcurrido en el servidor."
    segundos = duracion_ms / 1000
    for p in (pulsaciones_j1, pulsaciones_j2):
        if p / segundos > PULSACIONES_MAX_POR_SEG:
            return "La cantidad de pulsaciones por segundo no es humanamente posible."
    return None

