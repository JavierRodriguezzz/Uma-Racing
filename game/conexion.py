"""Conexión del juego con UmaRacing Online.

En el navegador el juego vive dentro de jugar.html (iframe). Esa página expone
window.umaBridge, que hace las peticiones a la API con la sesión del usuario;
el juego solo envía la petición y revisa cada frame si ya llegó la respuesta,
así nunca se congela la animación.

En escritorio no hay puente: el juego funciona sin conexión, como el original.
"""
import asyncio
import json
import sys

EN_NAVEGADOR = sys.platform == "emscripten"


class Conexion:
    def __init__(self):
        self.puente = None
        self._siguiente = 0
        if EN_NAVEGADOR:
            try:
                import platform  # módulo de pygbag con acceso a window
                puente = platform.window.parent.umaBridge
                if puente:
                    self.puente = puente
            except Exception as e:  # el juego se abrió fuera de jugar.html
                print("Sin puente con la página:", e)

    @property
    def en_linea(self):
        return self.puente is not None

    def enviar(self, metodo, ruta, cuerpo=None):
        """Inicia una petición y devuelve su id (o None si no hay conexión)."""
        if not self.en_linea:
            return None
        self._siguiente += 1
        pid = f"p{self._siguiente}"
        self.puente.pedir(pid, metodo, ruta, json.dumps(cuerpo) if cuerpo is not None else "")
        return pid

    def recoger(self, pid):
        """None mientras la respuesta no llega; después {'ok': bool, 'datos'|'mensaje': ...}."""
        if pid is None:
            return None
        texto = self.puente.resultado(pid)
        if not texto:
            return None
        return json.loads(str(texto))

    async def pedir(self, metodo, ruta, cuerpo=None, espera_max=10.0):
        """Versión que espera la respuesta cediendo el control al navegador."""
        pid = self.enviar(metodo, ruta, cuerpo)
        if pid is None:
            return {"ok": False, "mensaje": "Sin conexión"}
        transcurrido = 0.0
        while transcurrido < espera_max:
            r = self.recoger(pid)
            if r is not None:
                return r
            await asyncio.sleep(0.05)
            transcurrido += 0.05
        return {"ok": False, "mensaje": "El servidor tardó demasiado en responder"}
