# IA de las chibis del dormitorio

Diseño de los 5 NPC autónomos del dormitorio (`frontend/dormitorio.html`). El motor está en
`frontend/js/dormitorio/ia.js` y todos los números y guiones en `frontend/js/dormitorio/perfiles.js`:
para ajustar una personalidad se edita ese archivo, no el motor.

## Arquitectura

| Pieza | Responsabilidad |
|---|---|
| **Director** | Reloj día/noche (1 s real = 4 min del juego, ajustable con el reloj del HUD), sensores de percepción cada 0.3 s, reglas de interrupción, encuentros activos y la comida servida en la mesa. |
| **Habitante** | Necesidades, Utility AI para elegir la acción, ejecución (A* en la cuadrícula, uso de muebles) y poses. |
| **Encuentro** | Interacción entre dos chibis: acercarse → guion (líneas, poses, emotes) → efectos en sus necesidades → acción siguiente de cada una. |

Es un modelo híbrido: **Utility AI** para el comportamiento normal, **reglas con prioridad** que interrumpen
(como un árbol de comportamiento con selector de prioridad) y una **máquina de estados** de ejecución
(`libre → caminando → acomodando → usando`, o `encuentro`).

## Necesidades (0–100)

| Necesidad | Lo deseable | Sube con | Baja con |
|---|---|---|---|
| Energía | alta | dormir, descansar | el tiempo, correr, entrenar |
| Hambre | baja | el tiempo, entrenar | comer |
| Enfoque | alto | entrenar, patrullar, estar sola | el tiempo, travesuras |
| Social | alto | platicar, cocinar para otras | el tiempo |
| Estrés | bajo | multitudes (introvertidas), regaños, bromas | descansar, estar sola, comer |
| Diversión | alta | tele, travesuras, platicar | el tiempo |

Cada chibi multiplica la deriva con sus **ritmos**: Oguri tiene hambre ×2.4; Suzuka necesita socializar
×0.25; Stay Gold se aburre ×1.9; Fenomeno pierde enfoque ×1.7 y se cansa ×0.75.

## Utility AI

Cada vez que queda libre, la chibi puntúa todas sus acciones:

```
puntaje = curva(necesidades) × peso de la personalidad × horario (global × propio) + ruido(±0.025)
```

| Acción | Curva base |
|---|---|
| dormir | (1 − energía)² × 1.2 (+0.5 de madrugada, +0.35 después de las 22:00) |
| descansar | (1 − energía) × 0.55 + estrés × 0.35 |
| comer | hambre² × 1.3 (+0.12 si hay comida en la mesa) |
| pedir comida (Oguri) | hambre² × 1.4, si Akebono está disponible |
| cocinar (Akebono) | máx. necesidad de cuidado de las demás × 0.9 + 0.08 |
| entrenar | (1 − enfoque) × 0.9 (× 0.2 si energía < 30) |
| patrullar | (1 − enfoque) × 0.6 + 0.12 |
| tele / pasear | (1 − diversión) × 0.7 / 0.2 + (1 − diversión) × 0.2 |
| estar sola | estrés × 0.9 (+0.3 si hay 2 o más cerca) |
| travesura (Stay Gold) | (1 − diversión) × 0.9 + 0.1 |
| interactuar | la mejor utilidad de los encuentros posibles con quien percibe |

Un peso de 0 desactiva la acción para esa personalidad. Por ejemplo, solo Stay Gold hace travesuras y
solo Fenomeno patrulla. `horaDormir` evita que Fenomeno (23:00) y Stay Gold (23:45, noctámbula) se
duerman antes de esa hora salvo que estén agotadas.

## Reglas de interrupción

Se revisan cada 0.3 s. Una regla gana si su prioridad supera a la de la acción actual
(normal 2, comer o cocinar 4, encuentro 5, dormir 6).

| Regla | Quién | Prioridad | Condición | Acción |
|---|---|---|---|---|
| Hambre de Oguri | Oguri | 9 | hambre > 80 (la despierta) | busca a Akebono, si no puede, comida |
| Agotada | todas | 8 | energía < 12 | dormir |
| Multitud | Suzuka | 7 | 2 o más a ≤ 2.5 celdas y estrés > 30 | se aleja a la celda más lejana y mira por la ventana |
| Caos | Fenomeno | 7 | ve a alguien haciendo caos | regaño |
| Toque de queda | Fenomeno | 6 | 22:00–23:54 y ve a alguien despierta | la manda a dormir |
| Cuidar | Akebono | 5 | ve a alguien con necesidad de cuidado > 0.72 | cocina y le lleva comida |

Caos = estar subida en la mesa, haber hecho una broma hace menos de 8 s o correr vueltas de noche.

## Percepción

Cada chibi ve a las demás dentro de un radio y un campo de visión, y "oye" a las muy cercanas sin
importar hacia dónde mira. Dormida no percibe. El botón **IA** del dormitorio dibuja los conos.

| Chibi | Radio | Campo de visión | Oído |
|---|---|---|---|
| Silence Suzuka | 3.5 | 120° | 1.4 |
| Hishi Akebono | 4.5 | 210° (atenta a todas) | 2 |
| Oguri Cap | 3.5 | 150° | 1.5 |
| Fenomeno | 5.5 | 140° (vigilancia) | 2 |
| Stay Gold | 4 | 180° | 1.6 |

## Ciclo de vida y día/noche

```
llegar → libre ─(evalúa utilidades)→ ejecutar acción → libre → …
             ↑                              │
             └── regla de mayor prioridad ──┘   (interrumpe en cualquier momento)
```

| Fase | Horas | Efecto global |
|---|---|---|
| Madrugada | 0–6 | dormir ×3, casi todo lo demás ×0.2–0.3 |
| Mañana | 6–12 | entrenar ×1.5, comer ×1.15. Suzuka entrena ×2 y Fenomeno ×1.8 |
| Tarde | 12–19 | interactuar ×1.2, cocinar ×1.2. Fenomeno patrulla ×1.5 |
| Noche | 19–24 | dormir ×1.5, tele ×1.3. Stay Gold hace travesuras ×2 |

## Matriz de afinidad

Se lee de la fila hacia la columna (−1 choque, 1 la adora) y no es simétrica. Influye en con quién
platica, si acepta la plática y si la charla le relaja o le estresa.

| de \ hacia | Suzuka | Oguri | Akebono | Fenomeno | Stay Gold |
|---|---|---|---|---|---|
| **Suzuka** | — | 0.3 | 0.25 | 0.15 | −0.1 |
| **Oguri** | 0.3 | — | 0.95 | 0.1 | 0.2 |
| **Akebono** | 0.6 | 0.9 | — | 0.5 | 0.5 |
| **Fenomeno** | 0.45 | 0.2 | 0.4 | — | −0.6 |
| **Stay Gold** | 0.75 | 0.3 | 0.25 | −0.4 | — |

Probabilidad de aceptar una plática (si no es forzada):
`0.35 + 0.5·afinidad + 0.4·(1 − social) − introversión·0.5·(estrés + 0.4 si hay multitud)`.
Si Suzuka rechaza, se va a estar sola.

## Encuentros entre pares

| Encuentro | Pareja | Disparo | Resultado |
|---|---|---|---|
| Orden de entrenar | Fenomeno → Stay Gold | de día, enfoque de Stay Gold < 60 | 70 %: "Nop." y huye. 30 %: entrena de mala gana |
| Regaño | Fenomeno → quien hace caos | regla Caos | Stay Gold la desafía (65 %) y huye, las demás piden perdón |
| Toque de queda | Fenomeno → despiertas | 22:00+ | Stay Gold: "La noche es joven ♪", Oguri pide cenar, las demás se van a dormir |
| Despertar | Fenomeno → dormidas | 7:30–10:00 | Stay Gold: "Cinco minutitos más…" |
| Recordar el deber | Fenomeno → ociosas con poco enfoque | de día | Suzuka ya corrió, Oguri "después de comer", Akebono "¡primero hay que comer!" |
| Pedir comida | Oguri → Akebono | regla Hambre | Akebono cocina para ella y Oguri espera sentada |
| Ofrecer comida | Akebono → la más necesitada | al terminar de cocinar | Oguri come feliz. Suzuka acepta breve y cortés. Si nadie la necesita, deja el plato en la mesa |
| Calmar | Akebono → Fenomeno | estrés de Fenomeno > 60 | "…Cinco minutos." y descansa |
| Rareza | Stay Gold → Suzuka | aburrimiento | preguntas raras ("¿por qué siempre giras a la izquierda?") y corren juntas |
| Broma ("¡Bu!") | Stay Gold → cualquiera | aburrimiento (Fenomeno ×1.25) | Oguri ni se inmuta, Suzuka se asusta y se aleja, Fenomeno la castiga. Marca caos 8 s |
| Charla | cualquiera ↔ cualquiera | necesidad social × sociable × afinidad | diálogos propios por pareja o genéricos |

Cada encuentro tiene enfriamiento por pareja para no repetirse. Las líneas cambian la pose de quien habla
(señalar, brazos cruzados, ofrecer, cocinar, sorpresa, cansada…) y pueden mostrar un emote
(💢 ❗ ♪ 💧 💤 🍙 ❤ ✨ ❓).

## Cómo verlo

El dormitorio es una sección de la interfaz del juego: en **Jugar** está la pestaña **Dormitorio**
(o el enlace *Dormitorio* de la barra lateral, `/jugar.html#dormitorio`). Desde la selección de corredoras
también se abre con el botón **DORMITORIO** o la tecla <kbd>TAB</kbd>, y desde el dormitorio se regresa con
**Carreras**. Mientras se ve una sección la otra queda en pausa: la carrera no avanza ni suena (y ese tiempo no
cuenta en la duración que se envía al servidor) y el dormitorio deja de dibujar y detiene su reloj.

1. Inicia la app, entra como jugador y abre **Jugar → Dormitorio**. Consigue más chibis en **Chibis**.
   Para trabajar solo en el dormitorio sin la API: desde la carpeta `programacion web` ejecuta
   `python -m http.server 8770 --directory Uma-Racing/frontend` y abre `http://localhost:8770/dormitorio.html`.
2. Activa **IA** para ver la acción, las necesidades y los conos de visión de cada una.
3. Haz clic en una chibi para ver sus necesidades en vivo y los puntajes de su última decisión.
4. Haz clic en el reloj para acelerar el tiempo (×1, ×4, ×12, ×30) y ver el ciclo completo de día y noche.

Con sesión iniciada, el dormitorio usa la cuenta del jugador: las monedas reales, las chibis de su inventario y cada
pieza de mueble con su posición (`GET /api/dormitorio`, `POST /api/compras`, `PUT /api/dormitorio/acomodo`; ver
`frontend/js/dormitorio/almacen.js`). Sin sesión, como con el `http.server` del paso 1, funciona en **modo demo**: monedas
de prueba y muebles guardados en `localStorage`, con el botón **Reiniciar**.
