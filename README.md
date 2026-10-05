# UmaRacing

Juego de carreras para 2 jugadores hecho con Python y pygame. Funciona en escritorio y en el navegador (WebAssembly con [pygbag](https://pypi.org/project/pygbag/)).

## Estructura

```text
game/
├── main.py          # juego (async para poder ejecutarse en el navegador)
├── assets/          # imágenes (pre-escaladas) y audio OGG
└── requirements.txt
```

## Jugar en escritorio

```bash
pip install -r game/requirements.txt
python game/main.py
```

## Jugar en el navegador

```bash
pip install pygbag
python -X utf8 -m pygbag game
```

Abre http://localhost:8000 y haz clic en la página para iniciar (los navegadores exigen un clic antes de reproducir audio).

Para generar solo los archivos web (sin servidor):

```bash
python -X utf8 -m pygbag --build game
```

El resultado queda en `game/build/web/` (`index.html` + `game.apk`) y puede publicarse en cualquier servidor web estático. El intérprete de Python se descarga del CDN de pygame-web, por lo que el navegador necesita internet.

> `-X utf8` evita un error de codificación de pygbag en Windows.

## Controles

- Jugador 1: A / D (alternar para correr), W para confirmar
- Jugador 2: ← / → (alternar para correr), ↑ para confirmar
- F11: pantalla completa (en el navegador usa la pantalla completa del navegador)

Proyecto fan sin fines de lucro. Los personajes y la música pertenecen a sus respectivos dueños.
