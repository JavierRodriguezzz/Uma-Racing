"""Las pruebas usan su PROPIA base de datos (uma_racing_pruebas) para no modificar los datos reales.

Se recrea limpia al inicio de cada ejecución de pytest.
"""
import os
import sys
from pathlib import Path

BD_PRUEBAS = "uma_racing_pruebas"
os.environ["DB_NAME"] = BD_PRUEBAS          # debe fijarse ANTES de importar la app (config lee el entorno)

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "database"))
from reiniciar_bd import cargar  # noqa: E402


def pytest_sessionstart(session):
    cargar(BD_PRUEBAS)
