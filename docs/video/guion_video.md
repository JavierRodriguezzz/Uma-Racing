# Guion del video demostrativo — UmaRacing Online

**Duración objetivo:** 8 a 10 minutos · **Equipo 01** · Programación Web, grupo C

El profesor pidió un video con el flujo de la página web. El guion recorre el sistema en el orden en que lo usaría una persona y, de paso, muestra los requerimientos 1 a 20 (la columna **Req.** indica cuál se ve en cada escena). Conviene que cada integrante narre la parte de sus módulos:

- **Javier:** arquitectura, BD/API, autenticación, tienda y Google Pay.
- **Marco:** juego, partidas, logros, ranking, tiempo de juego y apuestas.
- **José:** publicidad, gachapón, usuarios y bitácora, dashboard y reportes.

---

## Antes de grabar

1. **Usa una base con datos demo** para que el dashboard y los reportes tengan información. No hace falta tocar tu base real `uma_racing`; carga la demo en una base aparte:
   ```bash
   backend/.venv/Scripts/python -c "import sys; sys.path.insert(0,'database'); import reiniciar_bd; reiniciar_bd.cargar('uma_racing_doc', demo=True)"
   ```
   Después arranca la configuración `api-doc` de `.claude/launch.json` (puerto **8010**, apunta a `uma_racing_doc`), o arranca uvicorn con `DB_NAME=uma_racing_doc`.
2. Abre `http://127.0.0.1:8010` en Chrome a pantalla completa, con zoom al 100 % y sin pestañas personales.
3. Ten listas dos ventanas: una **normal** para el jugador y una **de incógnito** para el administrador.
4. Abre **DevTools → Network** (filtro `Fetch/XHR`) cuando lo indique el guion. Ahí se ve que la página habla con la API en JSON.
5. Usuarios: `jugador1` / `Jugador123!` (con historial), `jugador2` / `Jugador123!` (350 monedas, ideal para el saldo insuficiente) y `admin` / `Admin123!`.
6. Graba con OBS o con la barra de juegos de Windows (`Win + Alt + R`), a 1080p y con micrófono.
7. Al terminar puedes borrar la base demo: `DROP DATABASE uma_racing_doc;`

---

## Escenas

| # | Tiempo | Qué mostrar en pantalla | Qué decir (idea) | Req. |
|---|---|---|---|---|
| 1 | 0:00–0:40 | Portada del PDF y luego el repositorio en GitHub (carpetas `frontend/`, `backend/`, `database/`, `docs/`). | “UmaRacing Online es un juego de carreras en el navegador con plataforma web, tienda, publicidad simulada y ranking. Está dividido en frontend, API REST con FastAPI y base MariaDB.” | 1, 2 |
| 2 | 0:40–1:10 | `database/schema.sql` (un `CREATE TABLE` con FK) y el diagrama ER del PDF (sección 9). | “26 tablas en tercera forma normal, con claves foráneas, restricciones e índices. El script crea la BD desde cero y `seed.sql` carga los datos de prueba.” | 3, 4 |
| 3 | 1:10–1:50 | `/registro.html`: envía el formulario vacío, después un correo inválido y luego un usuario que ya existe (`jugador1`). | “El frontend valida los campos, pero el backend vuelve a validar: el usuario repetido responde **409 Conflicto** con un mensaje claro.” | 17, 18, 7 |
| 4 | 1:50–2:30 | `/login.html`: primero una contraseña incorrecta (mensaje de error) y después `jugador1` correcto. En Network, la petición `POST /api/auth/login` y su respuesta JSON con el token. | “Las contraseñas se guardan con bcrypt; el login devuelve un token JWT con sesión revocable.” | 9, 6, 7 |
| 5 | 2:30–3:10 | Dashboard del jugador: tarjetas, saldo y actividad. | “Todo lo que se ve aquí viene de la API, nada está escrito en el HTML.” | 12 |
| 6 | 3:10–4:10 | **Jugar:** elegir una corredora y correr una carrera corta. Al terminar, ir a **Historial** y **Logros** para ver la partida y el logro registrados. | “El servidor valida el resultado; si llega un tiempo imposible, la partida se rechaza. Registrar la partida, dar monedas y otorgar logros ocurre en **una sola transacción**.” | 19, 20 |
| 7 | 4:10–4:50 | **Ver anuncios:** intenta cobrar antes de que termine el anuncio (error) y después déjalo terminar y cobra. El saldo sube. | “Ver anuncio → completar → recompensa. El servidor mide el tiempo; no basta con cambiar una variable en JavaScript. También hay límite diario.” | 19, 20 |
| 8 | 4:50–5:40 | **Tienda:** comprar un artículo con saldo suficiente. Luego entrar como `jugador2` (350 monedas) e intentar algo más caro. | “La compra descuenta saldo, entrega el artículo y registra el movimiento dentro de una transacción. Si algo falla, se hace rollback. Sin saldo suficiente responde **409** y no se modifica nada.” | 19, 20, 7 |
| 9 | 5:40–6:10 | **Gachapón** o **Apuestas** (una tirada o una apuesta pequeña) y luego **Ranking**. | “Otra operación transaccional: valida el saldo, calcula el resultado en el servidor y actualiza el saldo.” | 19, 20 |
| 10 | 6:10–6:40 | Como `jugador1`, escribe en la barra de direcciones `/admin/usuarios.html`. | “Aunque un jugador conozca la URL, la API responde **403**: los permisos se revisan en el backend, no solo en el menú.” | 10, 11, 7 |
| 11 | 6:40–7:50 | En incógnito, entra como `admin` → **Usuarios**: buscar un nombre, filtrar por rol o estado, ordenar por columna y cambiar de página. Después, **Artículos**: crear, editar y desactivar un artículo (confirmar el diálogo). | “CRUD completo con búsqueda, filtros, ordenamiento y paginación del lado del servidor. Las bajas son lógicas.” | 8, 13, 14, 15, 16 |
| 12 | 7:50–8:30 | En Network, la petición del listado (`?page=2&limit=…`) con su JSON `pagina / limite / total / totalPaginas / datos`. | “Este es el formato estándar de paginación de la API.” | 5, 6, 16 |
| 13 | 8:30–9:10 | **Dashboard admin** y **Reportes**: cambiar el rango de fechas para que se actualicen las gráficas. **Bitácora** al final. | “Los reportes y las gráficas salen de la base de datos según el rango que se elija; la bitácora guarda las operaciones importantes.” | 12 (y avance de 21, 23–25) |
| 14 | 9:10–9:40 | `http://127.0.0.1:8010/docs` (Swagger): abrir un endpoint y mostrar sus códigos de respuesta. Cerrar en la sección 10 del PDF. | “La API está documentada con OpenAPI; en el PDF está la tabla de endpoints, roles, entradas y respuestas.” | 5, 7 |

---

## Consejos

- Antes de grabar, haz un ensayo completo para que ninguna pantalla se quede “Cargando…”.
- Haz zoom (`Ctrl` + rueda) cuando muestres un mensaje de error o el JSON en Network.
- Si el juego tarda en cargar la primera vez, ábrelo una vez antes de grabar.
- No muestres el archivo `.env` ni contraseñas reales en pantalla.
- Si el video pasa de 10 minutos, recorta las escenas 9 y 14.
