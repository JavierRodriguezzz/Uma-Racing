"""Simulador de carreras para las apuestas. El resultado lo decide SIEMPRE el servidor.

Cada corredora avanza por turnos; su paso depende de sus atributos:
  - velocidad:   paso base durante toda la carrera
  - arranque:    bono en el primer 25 % del recorrido
  - resistencia: cuánto se frena en el último 40 %
más un componente aleatorio. El servidor devuelve las posiciones de cada turno para que
el navegador anime exactamente la carrera que ya se decidió.
"""
import random
from functools import lru_cache

DISTANCIA = 1000
MARGEN_CASA = 0.92        # se paga el 92 % del valor justo
MOMIO_MINIMO = 1.10
SIMULACIONES_MOMIO = 4000


def simular(corredoras, rng=None):
    """corredoras: [{id, velocidad, resistencia, arranque}, ...] → {orden, cuadros, llegada}"""
    rng = rng or random.SystemRandom()
    pos = [0.0] * len(corredoras)
    llegada = {}
    cuadros = []
    turno = 0
    while len(llegada) < len(corredoras) and turno < 400:
        turno += 1
        for i, c in enumerate(corredoras):
            if i in llegada:
                continue
            avance = pos[i] / DISTANCIA
            base = 14 + c["velocidad"] * 0.08
            if avance < 0.25:
                base += (c["arranque"] - 50) * 0.04
            elif avance > 0.6:
                base -= (100 - c["resistencia"]) * 0.05 * (avance - 0.6) * 2.5
            paso = max(4.0, rng.gauss(base, 3.2))
            pos[i] += paso
            if pos[i] >= DISTANCIA:
                llegada[i] = turno - (pos[i] - DISTANCIA) / paso   # turno fraccional exacto de llegada
        cuadros.append([round(min(p, DISTANCIA)) for p in pos])
    orden = sorted(llegada, key=llegada.get)
    return {
        "orden": [corredoras[i]["id"] for i in orden],
        "cuadros": cuadros,
        "llegada": {corredoras[i]["id"]: round(llegada[i], 3) for i in llegada},
    }


@lru_cache(maxsize=32)
def _probabilidades(atributos):
    rng = random.Random(20261006)  # semilla fija: los momios son estables para los mismos atributos
    corredoras = [{"id": i, "velocidad": v, "resistencia": r, "arranque": a} for i, (v, r, a) in enumerate(atributos)]
    victorias = [0] * len(corredoras)
    for _ in range(SIMULACIONES_MOMIO):
        victorias[simular(corredoras, rng)["orden"][0]] += 1
    return tuple(v / SIMULACIONES_MOMIO for v in victorias)


def momios(corredoras):
    """Momio decimal por corredora: lo que se recibe por cada moneda apostada si gana."""
    atributos = tuple((c["velocidad"], c["resistencia"], c["arranque"]) for c in corredoras)
    probs = _probabilidades(atributos)
    return {c["id"]: {"probabilidad": round(p, 4), "momio": max(MOMIO_MINIMO, round(MARGEN_CASA / max(p, 0.01), 2))}
            for c, p in zip(corredoras, probs)}


def momio_tiempo(objetivo_ms, duraciones_ganadas):
    """Reto de tiempo: probabilidad estimada con el historial de victorias del jugador
    (estimador de Laplace para no dar momios infinitos con pocos datos)."""
    n = len(duraciones_ganadas)
    exitos = sum(1 for d in duraciones_ganadas if d <= objetivo_ms)
    p = (exitos + 1) / (n + 2)
    return max(MOMIO_MINIMO, min(10.0, round(MARGEN_CASA / p, 2))), round(p, 4)
