# UmaRacing Online

Videojuego de carreras para 2 jugadores (Python + pygame) que se juega **en el navegador** e incorpora una plataforma web con
cuentas de usuario, tienda con monedas virtuales, compra de monedas con **Google Pay (modo TEST)**, monedas por **tiempo de
juego**, **apuestas** (carreras simuladas por el servidor y retos de tiempo), **gachapón** con probabilidades públicas,
publicidad simulada, ranking, logros, reportes y administración.

Interfaz "Arcade nocturno" con animaciones de [anime.js](https://animejs.com/).

**Proyecto final — Programación Web** · Grupo C · 7.º semestre
Docente: Francisco Hunahpu Sahagún González

| Integrantes |
|---|
| Javier Antonio Rodríguez Morales |
| Marco Antonio Muñoz Malpica |
| José Oliver Guzmán Camacho |

## Objetivo

Convertir un videojuego de escritorio en un sistema web cliente-servidor donde cada carrera, compra y recompensa se
registra y valida en el backend, con persistencia en una base de datos relacional, control de acceso por roles y
estadísticas para la toma de decisiones.

## Arquitectura

```text
Usuario ──► Frontend (HTML/CSS/JS) ──┐
                                     ├──► API REST (FastAPI) ──► Reglas de negocio ──► MariaDB
Jugador ──► Juego (pygame → WebAssembly) ──┘   (vía puente en jugar.html)
```

El frontend y el juego **nunca** acceden a la base de datos: todo pasa por la API con un token JWT.

## Tecnologías

| Capa | Tecnología |
|---|---|
| Juego | Python 3.11, pygame-ce, [pygbag](https://pypi.org/project/pygbag/) (WebAssembly) |
| Frontend | HTML5, CSS3, JavaScript (módulos ES), Chart.js, anime.js |
| Pagos | Google Pay API for Web (entorno TEST) |
| Backend | Python 3.11, FastAPI, Uvicorn, PyMySQL, bcrypt, PyJWT |
| Base de datos | MariaDB 10.6+ (compatible con MySQL 8 / XAMPP) |
| Pruebas | pytest + TestClient de FastAPI |

## Estructura

```text
├── backend/            API REST (FastAPI)
│   ├── app/
│   │   ├── routers/    endpoints por módulo
│   │   ├── services/   reglas de negocio, monedero, logros, bitácora
│   │   ├── schemas.py  validaciones de entrada
│   │   └── security.py autenticación y roles
│   └── tests/          pruebas automatizadas
├── frontend/           páginas web (jugador y administración)
├── game/               el juego (main.py) y sus assets
├── database/           schema.sql, seed.sql y su generador
└── .env.example        variables de entorno de ejemplo
```

## Requisitos

- Python 3.11
- MariaDB 10.6+ o MySQL 8 (por ejemplo, el de XAMPP)
- Navegador moderno con acceso a internet (el intérprete de Python para WebAssembly se descarga del CDN de pygame-web)

## Instalación

```bash
git clone https://github.com/Perrullo/Uma-Racing.git
cd Uma-Racing
python -m venv backend/.venv
backend/.venv/Scripts/activate        # Windows  (Linux/Mac: source backend/.venv/bin/activate)
pip install -r backend/requirements.txt
pip install pygbag
```

### Base de datos

Con MySQL/MariaDB encendido (en XAMPP: botón *Start* de MySQL):

```bash
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql
```

`schema.sql` crea la base `uma_racing` desde cero (23 tablas + 1 vista). Después carga **uno** de estos archivos:

| Archivo | Contenido |
|---|---|
| `seed.sql` | Inicio limpio: catálogo completo y las cuentas de prueba con todo en cero (sin monedas, partidas, compras ni logros; solo las corredoras gratuitas). |
| `seed_demo.sql` | Lo anterior más 60 días de actividad de 15 jugadores, útil para mostrar reportes y gráficas. |

Para regenerarlos: `python database/generar_seed.py` (limpio) o `python database/generar_seed.py --demo`.

**Reiniciar todo a cero en cualquier momento** (usa la conexión del `.env`):

```bash
python database/reiniciar_bd.py          # todo en cero
python database/reiniciar_bd.py --demo   # con datos de demostración
```

### Variables de entorno

Copia `.env.example` como `.env` en la raíz y ajusta los valores:

| Variable | Descripción |
|---|---|
| `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD` | conexión a MariaDB |
| `JWT_SECRET` | clave para firmar tokens (mínimo 32 caracteres) |
| `JWT_EXPIRA_HORAS` | duración de la sesión |
| `MONEDAS_REGISTRO` | bono de bienvenida |
| `ANUNCIOS_MAX_DIA` | anuncios con recompensa por día |
| `PARTIDAS_RECOMPENSA_MAX_DIA` | partidas con monedas por día |
| `GOOGLE_PAY_ENTORNO` | `TEST` (sin cobro). `PRODUCTION` requiere pasarela de pago |
| `TIEMPO_*` | monedas por tiempo de juego activo y tope diario |
| `APUESTA_*` | monto mínimo/máximo y pérdida neta máxima por día |
| `SERVIR_FRONTEND` | `true` para que la API también sirva el frontend y el juego (desarrollo) |

`.env` está en `.gitignore`: nunca se sube al repositorio.

## Ejecución

```bash
# 1. Compilar el juego para el navegador (genera game/build/web) con la plantilla propia
python -X utf8 -m pygbag --build --template plantilla_juego/umaracing.tmpl game

# 2. Iniciar la API (también sirve el frontend y el juego)
cd backend
uvicorn app.main:app --reload --port 8000
```

- Aplicación: http://localhost:8000
- Documentación interactiva de la API (Swagger): http://localhost:8000/docs

El juego también funciona en escritorio sin conexión: `python game/main.py`.

> **Importante:** compila siempre con `--template plantilla_juego/umaracing.tmpl`. La plantilla trae la pantalla de
> carga del juego y corrige un comportamiento de pygbag: en direcciones `http://localhost:8...` pide pygame a
> `http://localhost:8000/cdn/` (su servidor de pruebas) y el juego falla con `module 'pygame' has no attribute 'mixer'`.
> La plantilla fija el CDN público de paquetes para que funcione en cualquier servidor y puerto.

### Pruebas

```bash
cd backend
python -m pytest -v
```

Las pruebas usan su propia base de datos (`uma_racing_pruebas`), que se recrea al iniciar; nunca modifican `uma_racing`.

## Usuarios de prueba

| Usuario | Contraseña | Rol | Notas |
|---|---|---|---|
| `admin` | `Admin123!` | Administrador | |
| `jugador1` | `Jugador123!` | Jugador | en `seed.sql` empieza en cero; en `seed_demo.sql` tiene historial y todo desbloqueado |
| `jugador2` | `Jugador123!` | Jugador | en `seed.sql` empieza en cero; en `seed_demo.sql` tiene 350 monedas y Condor/Jungle bloqueados |
| demás jugadores de `seed_demo.sql` | `Demo1234!` | Jugador | |

## Endpoints principales

| Método | Endpoint | Descripción | Rol |
|---|---|---|---|
| POST | `/api/auth/registro` | Crear cuenta | Público |
| POST | `/api/auth/login` | Iniciar sesión (devuelve JWT) | Público |
| POST | `/api/auth/logout` | Cerrar sesión (revoca el token) | Autenticado |
| GET | `/api/items` | Catálogo con búsqueda, filtros, orden y paginación | Autenticado |
| POST / PUT / PATCH / DELETE | `/api/items[/{id}]` | CRUD de artículos | Administrador |
| POST | `/api/compras` | Comprar un artículo (transacción) | Jugador |
| POST | `/api/compras/{folio}/reembolso` | Reembolsar (transacción) | Administrador |
| POST | `/api/anuncios/{id}/ver` · `/api/anuncios/visualizaciones/{token}/completar` | Ver anuncio y reclamar recompensa | Jugador |
| POST | `/api/partidas` · `/api/partidas/{token}/finalizar` | Registrar partida (validada por el servidor) | Jugador |
| GET | `/api/ranking` | Ranking por periodo y criterio | Autenticado |
| GET / POST / PUT / PATCH / DELETE | `/api/paquetes[/{id}]` | Paquetes de monedas (CRUD admin) | Autenticado / Administrador |
| POST | `/api/pagos/ordenes` · `/api/pagos/ordenes/{folio}/confirmar` | Comprar monedas con Google Pay (transacción) | Jugador |
| POST | `/api/tiempo-juego/sesiones` · `/{token}/latido` | Monedas por tiempo de juego activo | Jugador |
| GET / POST | `/api/apuestas/carrera` | Momios y apuesta a carrera simulada por el servidor | Jugador |
| GET / POST / DELETE | `/api/apuestas/tiempo/cotizar` · `/api/apuestas/tiempo` · `/api/apuestas/{folio}` | Reto de tiempo | Jugador |
| GET / POST | `/api/gacha` · `/api/gacha/tiradas` | Gachapón (probabilidades, tiradas ×1 / ×10) | Jugador |
| GET / POST / PUT / DELETE | `/api/gacha/premios[/{id}]` | Premios del gachapón | Administrador |
| GET | `/api/logros` | Logros y progreso | Autenticado |
| GET / POST / PUT / PATCH / DELETE | `/api/usuarios[/{id}]` | Administración de usuarios | Administrador |
| GET | `/api/dashboard` | Indicadores según el rol | Autenticado |
| GET | `/api/reportes/{ventas,partidas,economia,monetizacion}` | Reportes por rango de fechas | Administrador |
| GET | `/api/bitacora` | Historial de operaciones | Administrador |

La lista completa, con parámetros, cuerpos y respuestas, está en `/docs` (OpenAPI).

## Reglas de las nuevas mecánicas

- **Google Pay (TEST):** el servidor crea la orden con el precio del paquete; el navegador solo confirma con el token de Google.
  Una orden se paga una sola vez y vence en 15 minutos. Sin cobro real.
- **Tiempo de juego:** 5 monedas por cada 5 minutos con actividad (teclas), medidos con latidos del servidor; máximo 60 al día.
- **Apuestas:** de 10 a 500 monedas, pérdida neta máxima de 1,500 al día. En la carrera simulada el resultado lo decide el
  servidor; los momios salen de 4,000 simulaciones con 8 % de margen. El reto de tiempo se resuelve con tu siguiente partida.
- **Gachapón:** 100 monedas (×10: 900). Común 75 %, rara 22 %, épica 3 %; épica garantizada a las 30 tiradas sin épica;
  los repetidos se compensan con monedas.

Todas las monedas son virtuales y no tienen valor monetario.

## Controles del juego

- Jugador 1 (tu cuenta): <kbd>A</kbd>/<kbd>D</kbd> elegir y correr, <kbd>W</kbd> confirmar
- Jugador 2 (invitado): <kbd>←</kbd>/<kbd>→</kbd> elegir y correr, <kbd>↑</kbd> confirmar

Proyecto fan con fines académicos y sin fines de lucro. Los personajes y la música pertenecen a sus respectivos dueños.
La publicidad es simulada y las monedas son virtuales.
