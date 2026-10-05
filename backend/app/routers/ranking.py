"""/api/ranking — clasificación de jugadores por periodo y criterio."""
from fastapi import APIRouter, Depends, Query

from ..db import get_db, todos
from ..security import usuario_actual

router = APIRouter(prefix="/api/ranking", tags=["Ranking"])

PERIODOS = {"semana": "NOW() - INTERVAL 7 DAY", "mes": "NOW() - INTERVAL 30 DAY", "total": None}
CRITERIOS = {"puntaje": "puntaje_total DESC", "victorias": "victorias DESC, puntaje_total DESC",
             "mejor_tiempo": "mejor_tiempo_ms IS NULL, mejor_tiempo_ms ASC"}


@router.get("", summary="Ranking por periodo (semana, mes, total) y criterio (puntaje, victorias, mejor_tiempo)")
def ranking(periodo: str = Query("total", pattern="^(semana|mes|total)$"),
            criterio: str = Query("puntaje", pattern="^(puntaje|victorias|mejor_tiempo)$"),
            limit: int = Query(20, ge=1, le=100),
            usuario=Depends(usuario_actual), conn=Depends(get_db)):
    desde = PERIODOS[periodo]
    filtro_fecha = f"AND pa.iniciada_en >= {desde}" if desde else ""  # valores de lista blanca, no del usuario
    filas = todos(conn, f"""
        SELECT u.id AS usuario_id, u.username, p.nombre_mostrar, fav.codigo AS personaje_favorito,
               COUNT(pa.id) AS partidas, COALESCE(SUM(pa.ganador = 'J1'), 0) AS victorias,
               COALESCE(SUM(pa.puntaje), 0) AS puntaje_total, COALESCE(MAX(pa.puntaje), 0) AS mejor_puntaje,
               MIN(CASE WHEN pa.ganador = 'J1' THEN pa.duracion_ms END) AS mejor_tiempo_ms
        FROM usuarios u
        JOIN roles r ON r.id = u.rol_id AND r.nombre = 'jugador'
        JOIN perfiles p ON p.usuario_id = u.id
        LEFT JOIN items fav ON fav.id = p.personaje_favorito_id
        JOIN partidas pa ON pa.usuario_id = u.id AND pa.estado = 'finalizada' {filtro_fecha}
        WHERE u.activo = 1 AND u.eliminado_en IS NULL
        GROUP BY u.id, u.username, p.nombre_mostrar, fav.codigo
        ORDER BY {CRITERIOS[criterio]}
    """)
    for i, f in enumerate(filas, start=1):
        f["posicion"] = i
        f["porcentaje_victorias"] = round(100 * int(f["victorias"]) / f["partidas"], 1) if f["partidas"] else 0
    mia = next((f for f in filas if f["usuario_id"] == usuario["id"]), None)
    return {"periodo": periodo, "criterio": criterio, "datos": filas[:limit], "mi_posicion": mia,
            "total_jugadores": len(filas)}
