"""Gachapón: rarezas con probabilidades públicas y garantía de épica (sistema de piedad)."""
import random

PROB_RAREZA = {"comun": 0.75, "rara": 0.22, "epica": 0.03}
GARANTIA_EPICA = 30          # la tirada número 30 sin épica es épica segura
COSTO_TIRADA = 100
COSTO_DIEZ = 900             # 10 tiradas con 10 % de descuento


def probabilidades(premios):
    """Probabilidad final de cada premio = P(rareza) × peso / suma de pesos de esa rareza."""
    pesos = {}
    for p in premios:
        pesos[p["rareza"]] = pesos.get(p["rareza"], 0) + p["peso"]
    return {p["id"]: round(PROB_RAREZA[p["rareza"]] * p["peso"] / pesos[p["rareza"]], 5) for p in premios}


def tirar(premios, sin_epica, rng=None):
    """Elige un premio. Devuelve (premio, por_garantia, nuevo_contador_sin_epica)."""
    rng = rng or random.SystemRandom()
    por_rareza = {}
    for p in premios:
        por_rareza.setdefault(p["rareza"], []).append(p)

    por_garantia = sin_epica + 1 >= GARANTIA_EPICA and "epica" in por_rareza
    if por_garantia:
        rareza = "epica"
    else:
        disponibles = [r for r in PROB_RAREZA if r in por_rareza]
        total = sum(PROB_RAREZA[r] for r in disponibles)
        x = rng.random() * total
        for rareza in disponibles:
            x -= PROB_RAREZA[rareza]
            if x <= 0:
                break
    opciones = por_rareza[rareza]
    premio = rng.choices(opciones, weights=[p["peso"] for p in opciones])[0]
    return premio, por_garantia, 0 if rareza == "epica" else sin_epica + 1
