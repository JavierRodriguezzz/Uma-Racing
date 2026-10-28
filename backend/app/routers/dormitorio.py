"""/api/dormitorio — el dormitorio del jugador: chibis, muebles y su acomodo.

Las chibis y los muebles se compran con POST /api/compras (misma transacción, folio, logros y
reembolsos que el resto de la tienda). Las chibis exclusivas salen en el gachapón.
"""
from fastapi import APIRouter, Depends

from ..db import get_db
from ..schemas import AcomodoIn
from ..security import solo_jugador
from ..services import dormitorio

router = APIRouter(prefix="/api/dormitorio", tags=["Dormitorio"])


@router.get("", summary="Estado del dormitorio: monedas, catálogo, chibis y muebles (lo crea la primera vez)")
def obtener(usuario=Depends(solo_jugador), conn=Depends(get_db)):
    dormitorio.asegurar(conn, usuario["id"])
    return dormitorio.estado(conn, usuario["id"])


@router.put("/acomodo", summary="Guardar dónde está cada mueble (el servidor valida que quepa y no se encime)")
def acomodar(datos: AcomodoIn, usuario=Depends(solo_jugador), conn=Depends(get_db)):
    dormitorio.asegurar(conn, usuario["id"])
    colocadas = dormitorio.guardar_acomodo(conn, usuario["id"], datos.piezas)
    return {"mensaje": "Acomodo guardado.", "colocadas": colocadas}
