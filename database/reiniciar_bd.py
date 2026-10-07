"""Reinicia la base de datos desde cero: borra todo y carga schema.sql + seed.sql.

Uso (desde la carpeta Uma-Racing):
    python database/reiniciar_bd.py            -> todo en cero (seed.sql)
    python database/reiniciar_bd.py --demo     -> con 60 días de actividad de ejemplo (seed_demo.sql)

Toma la conexión del archivo .env (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME).
Requiere: pip install pymysql python-dotenv
"""
import os
import sys
from pathlib import Path

import pymysql
from dotenv import load_dotenv
from pymysql.constants import CLIENT

CARPETA = Path(__file__).resolve().parent
load_dotenv(CARPETA.parent / ".env")


def cargar(nombre_bd: str, demo: bool = False):
    """Crea (o recrea) `nombre_bd` con el esquema y los datos iniciales."""
    if not nombre_bd.replace("_", "").isalnum():
        raise ValueError("Nombre de base de datos inválido.")
    schema = (CARPETA / "schema.sql").read_text(encoding="utf-8")
    seed = (CARPETA / ("seed_demo.sql" if demo else "seed.sql")).read_text(encoding="utf-8")
    # Los archivos usan la base `uma_racing`; se reemplaza por la indicada
    schema = schema.replace("uma_racing", nombre_bd)
    seed = seed.replace("USE uma_racing;", f"USE {nombre_bd};")

    conn = pymysql.connect(host=os.getenv("DB_HOST", "localhost"), port=int(os.getenv("DB_PORT", 3306)),
                           user=os.getenv("DB_USER", "root"), password=os.getenv("DB_PASSWORD", ""),
                           charset="utf8mb4", client_flag=CLIENT.MULTI_STATEMENTS, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{nombre_bd}`")
            for script in (schema, seed):
                cur.execute(script)
                while cur.nextset():   # consumir los resultados de cada sentencia
                    pass
            cur.execute(f"SELECT (SELECT COUNT(*) FROM `{nombre_bd}`.usuarios), (SELECT COALESCE(SUM(monedas), 0) FROM `{nombre_bd}`.perfiles), "
                        f"(SELECT COUNT(*) FROM `{nombre_bd}`.partidas)")
            return cur.fetchone()
    finally:
        conn.close()


if __name__ == "__main__":
    demo = "--demo" in sys.argv
    bd = os.getenv("DB_NAME", "uma_racing")
    usuarios, monedas, partidas = cargar(bd, demo)
    print(f"Base '{bd}' reiniciada ({'datos de demostración' if demo else 'todo en cero'}): "
          f"{usuarios} usuarios, {monedas} monedas, {partidas} partidas.")
