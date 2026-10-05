# UmaRacing Online

Videojuego de carreras para 2 jugadores (Python + pygame) que se juega **en el navegador** e incorpora una plataforma web con
cuentas de usuario, tienda con monedas virtuales, publicidad simulada con recompensas validadas por el servidor, ranking,
logros, reportes y administración.

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
| Frontend | HTML5, CSS3, JavaScript (módulos ES), Chart.js |
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

`schema.sql` crea la base `uma_racing` desde cero (15 tablas + 1 vista). `seed.sql` carga 60 días de datos de prueba.
Para regenerar el seed: `python database/generar_seed.py`.

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
| `SERVIR_FRONTEND` | `true` para que la API también sirva el frontend y el juego (desarrollo) |

`.env` está en `.gitignore`: nunca se sube al repositorio.

## Ejecución

```bash
# 1. Compilar el juego para el navegador (genera game/build/web)
python -X utf8 -m pygbag --build game

# 2. Iniciar la API (también sirve el frontend y el juego)
cd backend
uvicorn app.main:app --reload --port 8000
```

- Aplicación: http://localhost:8000
- Documentación interactiva de la API (Swagger): http://localhost:8000/docs

El juego también funciona en escritorio sin conexión: `python game/main.py`.

### Pruebas

```bash
cd backend
python -m pytest -v
```

## Usuarios de prueba

| Usuario | Contraseña | Rol | Notas |
|---|---|---|---|
| `admin` | `Admin123!` | Administrador | |
| `jugador1` | `Jugador123!` | Jugador | historial completo, todo desbloqueado |
| `jugador2` | `Jugador123!` | Jugador | Condor y Jungle bloqueados, 350 monedas |
| demás jugadores del seed | `Demo1234!` | Jugador | |

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
| GET | `/api/logros` | Logros y progreso | Autenticado |
| GET / POST / PUT / PATCH / DELETE | `/api/usuarios[/{id}]` | Administración de usuarios | Administrador |
| GET | `/api/dashboard` | Indicadores según el rol | Autenticado |
| GET | `/api/reportes/{ventas,partidas,economia}` | Reportes por rango de fechas | Administrador |
| GET | `/api/bitacora` | Historial de operaciones | Administrador |

La lista completa, con parámetros, cuerpos y respuestas, está en `/docs` (OpenAPI).

## Controles del juego

- Jugador 1 (tu cuenta): <kbd>A</kbd>/<kbd>D</kbd> elegir y correr, <kbd>W</kbd> confirmar
- Jugador 2 (invitado): <kbd>←</kbd>/<kbd>→</kbd> elegir y correr, <kbd>↑</kbd> confirmar

Proyecto fan con fines académicos y sin fines de lucro. Los personajes y la música pertenecen a sus respectivos dueños.
La publicidad es simulada y las monedas son virtuales.
