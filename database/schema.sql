-- =====================================================================
--  UmaRacing Online — Esquema de base de datos (MariaDB 10.6+ / MySQL 8)
--  Crea la base de datos desde cero. Normalizada a 3FN.
--  Uso:  mysql -u root -p < database/schema.sql
-- =====================================================================

CREATE DATABASE IF NOT EXISTS uma_racing
    CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE uma_racing;

SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS gacha_resultados;
DROP TABLE IF EXISTS gacha_tiradas;
DROP TABLE IF EXISTS gacha_premios;
DROP TABLE IF EXISTS apuestas;
DROP TABLE IF EXISTS atributos_carrera;
DROP TABLE IF EXISTS sesiones_juego;
DROP TABLE IF EXISTS ordenes_pago;
DROP TABLE IF EXISTS paquetes_monedas;
DROP TABLE IF EXISTS bitacora;
DROP TABLE IF EXISTS usuario_logros;
DROP TABLE IF EXISTS logros;
DROP TABLE IF EXISTS partidas;
DROP TABLE IF EXISTS visualizaciones_anuncio;
DROP TABLE IF EXISTS anuncios;
DROP TABLE IF EXISTS movimientos_monedas;
DROP TABLE IF EXISTS inventario_usuario;
DROP TABLE IF EXISTS compras;
DROP TABLE IF EXISTS perfiles;
DROP TABLE IF EXISTS items;
DROP TABLE IF EXISTS tipos_item;
DROP TABLE IF EXISTS sesiones;
DROP TABLE IF EXISTS usuarios;
DROP TABLE IF EXISTS roles;
SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------
-- 1. ROLES
-- ---------------------------------------------------------------------
CREATE TABLE roles (
    id          TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    nombre      VARCHAR(30)      NOT NULL,
    descripcion VARCHAR(150)     NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_roles_nombre UNIQUE (nombre)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 2. USUARIOS (credenciales y estado de la cuenta)
-- ---------------------------------------------------------------------
CREATE TABLE usuarios (
    id             INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    rol_id         TINYINT UNSIGNED NOT NULL,
    username       VARCHAR(30)      NOT NULL,
    email          VARCHAR(120)     NOT NULL,
    password_hash  VARCHAR(255)     NOT NULL,
    activo         TINYINT(1)       NOT NULL DEFAULT 1,
    ultimo_acceso  DATETIME         NULL,
    creado_en      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    eliminado_en   DATETIME         NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_usuarios_username UNIQUE (username),
    CONSTRAINT uq_usuarios_email    UNIQUE (email),
    CONSTRAINT fk_usuarios_rol FOREIGN KEY (rol_id) REFERENCES roles (id),
    CONSTRAINT ck_usuarios_username CHECK (CHAR_LENGTH(username) BETWEEN 3 AND 30),
    CONSTRAINT ck_usuarios_activo   CHECK (activo IN (0, 1)),
    INDEX ix_usuarios_creado (creado_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 3. SESIONES (permite cerrar sesión revocando el token en el servidor)
-- ---------------------------------------------------------------------
CREATE TABLE sesiones (
    id          INT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id  INT UNSIGNED NOT NULL,
    jti         CHAR(36)     NOT NULL,
    ip          VARCHAR(45)  NULL,
    user_agent  VARCHAR(255) NULL,
    creada_en   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_en   DATETIME     NOT NULL,
    revocada_en DATETIME     NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_sesiones_jti UNIQUE (jti),
    CONSTRAINT fk_sesiones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    INDEX ix_sesiones_usuario (usuario_id, creada_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 4. TIPOS DE ITEM (catálogo: personaje, escenario)
-- ---------------------------------------------------------------------
CREATE TABLE tipos_item (
    id     TINYINT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo VARCHAR(20)      NOT NULL,
    nombre VARCHAR(40)      NOT NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_tipos_item_codigo UNIQUE (codigo)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 5. ITEMS (productos de la tienda: personajes y escenarios)
--    `codigo` es el identificador que usa el juego para cargar sus assets.
-- ---------------------------------------------------------------------
CREATE TABLE items (
    id             INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    tipo_id        TINYINT UNSIGNED NOT NULL,
    codigo         VARCHAR(40)      NOT NULL,
    nombre         VARCHAR(60)      NOT NULL,
    descripcion    VARCHAR(255)     NOT NULL DEFAULT '',
    precio         INT UNSIGNED     NOT NULL DEFAULT 0,
    es_gratuito    TINYINT(1)       NOT NULL DEFAULT 0,
    imagen_url     VARCHAR(255)     NULL,
    activo         TINYINT(1)       NOT NULL DEFAULT 1,
    creado_en      DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_items_codigo UNIQUE (codigo),
    CONSTRAINT fk_items_tipo FOREIGN KEY (tipo_id) REFERENCES tipos_item (id),
    CONSTRAINT ck_items_precio   CHECK (precio <= 100000),
    CONSTRAINT ck_items_gratuito CHECK ((es_gratuito = 1 AND precio = 0) OR (es_gratuito = 0 AND precio > 0)),
    INDEX ix_items_tipo (tipo_id, activo)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 6. PERFILES (datos públicos del jugador + monedero)
-- ---------------------------------------------------------------------
CREATE TABLE perfiles (
    usuario_id            INT UNSIGNED NOT NULL,
    nombre_mostrar        VARCHAR(50)  NOT NULL,
    biografia             VARCHAR(255) NOT NULL DEFAULT '',
    monedas               INT UNSIGNED NOT NULL DEFAULT 0,
    personaje_favorito_id INT UNSIGNED NULL,
    escenario_equipado_id INT UNSIGNED NULL,
    tiradas_sin_epica     SMALLINT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (usuario_id),
    CONSTRAINT fk_perfiles_usuario   FOREIGN KEY (usuario_id)            REFERENCES usuarios (id),
    CONSTRAINT fk_perfiles_favorito  FOREIGN KEY (personaje_favorito_id) REFERENCES items (id),
    CONSTRAINT fk_perfiles_escenario FOREIGN KEY (escenario_equipado_id) REFERENCES items (id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 7. COMPRAS (venta de un item con folio único)
-- ---------------------------------------------------------------------
CREATE TABLE compras (
    id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
    folio            VARCHAR(24)  NOT NULL,
    usuario_id       INT UNSIGNED NOT NULL,
    item_id          INT UNSIGNED NOT NULL,
    precio_pagado    INT UNSIGNED NOT NULL,
    estado           ENUM('completada', 'reembolsada') NOT NULL DEFAULT 'completada',
    creada_en        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reembolsada_en   DATETIME     NULL,
    reembolsada_por  INT UNSIGNED NULL,
    motivo_reembolso VARCHAR(255) NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_compras_folio UNIQUE (folio),
    CONSTRAINT fk_compras_usuario     FOREIGN KEY (usuario_id)      REFERENCES usuarios (id),
    CONSTRAINT fk_compras_item        FOREIGN KEY (item_id)         REFERENCES items (id),
    CONSTRAINT fk_compras_reembolsada FOREIGN KEY (reembolsada_por) REFERENCES usuarios (id),
    CONSTRAINT ck_compras_precio CHECK (precio_pagado > 0),
    INDEX ix_compras_fecha (creada_en),
    INDEX ix_compras_usuario (usuario_id, creada_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 8. INVENTARIO (items que posee cada usuario; los gratuitos no se guardan)
-- ---------------------------------------------------------------------
CREATE TABLE inventario_usuario (
    id           INT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id   INT UNSIGNED NOT NULL,
    item_id      INT UNSIGNED NOT NULL,
    compra_id    INT UNSIGNED NULL,
    origen       ENUM('compra', 'regalo', 'logro', 'gacha') NOT NULL DEFAULT 'compra',
    adquirido_en DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_inventario UNIQUE (usuario_id, item_id),
    CONSTRAINT fk_inventario_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    CONSTRAINT fk_inventario_item    FOREIGN KEY (item_id)    REFERENCES items (id),
    CONSTRAINT fk_inventario_compra  FOREIGN KEY (compra_id)  REFERENCES compras (id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 9. MOVIMIENTOS DE MONEDAS (libro mayor del monedero virtual)
-- ---------------------------------------------------------------------
CREATE TABLE movimientos_monedas (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id     INT UNSIGNED    NOT NULL,
    tipo           ENUM('registro', 'compra', 'reembolso', 'anuncio', 'partida', 'logro', 'ajuste',
                        'compra_monedas', 'tiempo_juego', 'apuesta', 'premio_apuesta', 'gacha', 'premio_gacha') NOT NULL,
    monto          INT             NOT NULL,
    saldo_anterior INT UNSIGNED    NOT NULL,
    saldo_nuevo    INT UNSIGNED    NOT NULL,
    referencia     VARCHAR(40)     NULL,
    descripcion    VARCHAR(255)    NOT NULL,
    creado_en      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_movimientos_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    CONSTRAINT ck_movimientos_monto CHECK (monto <> 0),
    CONSTRAINT ck_movimientos_saldo CHECK (saldo_nuevo = saldo_anterior + monto),
    INDEX ix_movimientos_usuario (usuario_id, creado_en),
    INDEX ix_movimientos_fecha (creado_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 10. ANUNCIOS (publicidad simulada)
-- ---------------------------------------------------------------------
CREATE TABLE anuncios (
    id                 INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    titulo             VARCHAR(80)       NOT NULL,
    anunciante         VARCHAR(80)       NOT NULL,
    descripcion        VARCHAR(255)      NOT NULL DEFAULT '',
    color              CHAR(7)           NOT NULL DEFAULT '#3b82f6',
    duracion_seg       SMALLINT UNSIGNED NOT NULL,
    recompensa_monedas SMALLINT UNSIGNED NOT NULL,
    activo             TINYINT(1)        NOT NULL DEFAULT 1,
    creado_en          DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en     DATETIME          NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT ck_anuncios_duracion   CHECK (duracion_seg BETWEEN 5 AND 120),
    CONSTRAINT ck_anuncios_recompensa CHECK (recompensa_monedas BETWEEN 1 AND 500)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 11. VISUALIZACIONES DE ANUNCIO (el servidor valida la recompensa)
-- ---------------------------------------------------------------------
CREATE TABLE visualizaciones_anuncio (
    id                INT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id        INT UNSIGNED NOT NULL,
    anuncio_id        INT UNSIGNED NOT NULL,
    token             CHAR(36)     NOT NULL,
    estado            ENUM('iniciada', 'completada', 'rechazada') NOT NULL DEFAULT 'iniciada',
    iniciada_en       DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    completada_en     DATETIME(3)  NULL,
    monedas_otorgadas INT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    CONSTRAINT uq_visualizaciones_token UNIQUE (token),
    CONSTRAINT fk_visualizaciones_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    CONSTRAINT fk_visualizaciones_anuncio FOREIGN KEY (anuncio_id) REFERENCES anuncios (id),
    INDEX ix_visualizaciones_usuario (usuario_id, iniciada_en),
    INDEX ix_visualizaciones_fecha (iniciada_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 12. PARTIDAS (carreras registradas por el juego)
--     J1 es el usuario con sesión; J2 juega como invitado.
-- ---------------------------------------------------------------------
CREATE TABLE partidas (
    id               INT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id       INT UNSIGNED NOT NULL,
    token            CHAR(36)     NOT NULL,
    personaje_j1_id  INT UNSIGNED NOT NULL,
    personaje_j2_id  INT UNSIGNED NOT NULL,
    escenario_id     INT UNSIGNED NOT NULL,
    estado           ENUM('en_curso', 'finalizada', 'invalida') NOT NULL DEFAULT 'en_curso',
    ganador          ENUM('J1', 'J2') NULL,
    duracion_ms      INT UNSIGNED NULL,
    pulsaciones_j1   INT UNSIGNED NULL,
    pulsaciones_j2   INT UNSIGNED NULL,
    puntaje          INT UNSIGNED NOT NULL DEFAULT 0,
    monedas_ganadas  INT UNSIGNED NOT NULL DEFAULT 0,
    motivo_invalida  VARCHAR(255) NULL,
    iniciada_en      DATETIME(3)  NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
    finalizada_en    DATETIME(3)  NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_partidas_token UNIQUE (token),
    CONSTRAINT fk_partidas_usuario   FOREIGN KEY (usuario_id)      REFERENCES usuarios (id),
    CONSTRAINT fk_partidas_pj1       FOREIGN KEY (personaje_j1_id) REFERENCES items (id),
    CONSTRAINT fk_partidas_pj2       FOREIGN KEY (personaje_j2_id) REFERENCES items (id),
    CONSTRAINT fk_partidas_escenario FOREIGN KEY (escenario_id)    REFERENCES items (id),
    INDEX ix_partidas_usuario (usuario_id, iniciada_en),
    INDEX ix_partidas_fecha (iniciada_en),
    INDEX ix_partidas_estado (estado)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 13. LOGROS (catálogo configurable por el administrador)
-- ---------------------------------------------------------------------
CREATE TABLE logros (
    id                 INT UNSIGNED NOT NULL AUTO_INCREMENT,
    codigo             VARCHAR(40)  NOT NULL,
    nombre             VARCHAR(60)  NOT NULL,
    descripcion        VARCHAR(255) NOT NULL,
    condicion          ENUM('partidas_jugadas', 'victorias', 'anuncios_vistos', 'compras', 'puntaje_partida') NOT NULL,
    valor_objetivo     INT UNSIGNED NOT NULL,
    recompensa_monedas INT UNSIGNED NOT NULL DEFAULT 0,
    activo             TINYINT(1)   NOT NULL DEFAULT 1,
    creado_en          DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_logros_codigo UNIQUE (codigo),
    CONSTRAINT ck_logros_objetivo   CHECK (valor_objetivo > 0),
    CONSTRAINT ck_logros_recompensa CHECK (recompensa_monedas <= 5000)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 14. LOGROS OBTENIDOS POR USUARIO
-- ---------------------------------------------------------------------
CREATE TABLE usuario_logros (
    usuario_id  INT UNSIGNED NOT NULL,
    logro_id    INT UNSIGNED NOT NULL,
    obtenido_en DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, logro_id),
    CONSTRAINT fk_usuario_logros_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    CONSTRAINT fk_usuario_logros_logro   FOREIGN KEY (logro_id)   REFERENCES logros (id),
    INDEX ix_usuario_logros_fecha (obtenido_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 15. BITÁCORA (historial de operaciones importantes)
-- ---------------------------------------------------------------------
CREATE TABLE bitacora (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id      INT UNSIGNED    NULL,
    accion          VARCHAR(40)     NOT NULL,
    entidad         VARCHAR(40)     NOT NULL,
    entidad_id      VARCHAR(40)     NULL,
    estado_anterior TEXT            NULL,
    estado_nuevo    TEXT            NULL,
    ip              VARCHAR(45)     NULL,
    creado_en       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT fk_bitacora_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    INDEX ix_bitacora_fecha (creado_en),
    INDEX ix_bitacora_entidad (entidad, entidad_id)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 16. PAQUETES DE MONEDAS (se compran con Google Pay)
-- ---------------------------------------------------------------------
CREATE TABLE paquetes_monedas (
    id             INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    nombre         VARCHAR(60)   NOT NULL,
    monedas        INT UNSIGNED  NOT NULL,
    bonus          INT UNSIGNED  NOT NULL DEFAULT 0,
    precio_mxn     DECIMAL(8, 2) NOT NULL,
    destacado      TINYINT(1)    NOT NULL DEFAULT 0,
    activo         TINYINT(1)    NOT NULL DEFAULT 1,
    creado_en      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    actualizado_en DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT ck_paquetes_monedas CHECK (monedas BETWEEN 1 AND 1000000),
    CONSTRAINT ck_paquetes_precio  CHECK (precio_mxn > 0 AND precio_mxn <= 10000)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 17. ÓRDENES DE PAGO (el servidor fija el precio; el cliente solo confirma)
-- ---------------------------------------------------------------------
CREATE TABLE ordenes_pago (
    id              INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    folio           VARCHAR(24)   NOT NULL,
    usuario_id      INT UNSIGNED  NOT NULL,
    paquete_id      INT UNSIGNED  NOT NULL,
    monedas         INT UNSIGNED  NOT NULL,
    monto           DECIMAL(8, 2) NOT NULL,
    moneda          CHAR(3)       NOT NULL DEFAULT 'MXN',
    proveedor       VARCHAR(20)   NOT NULL DEFAULT 'google_pay',
    entorno         ENUM('TEST', 'PRODUCTION') NOT NULL DEFAULT 'TEST',
    estado          ENUM('pendiente', 'pagada', 'cancelada', 'expirada') NOT NULL DEFAULT 'pendiente',
    referencia_pago CHAR(64)      NULL,
    red_tarjeta     VARCHAR(20)   NULL,
    creada_en       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expira_en       DATETIME      NOT NULL,
    pagada_en       DATETIME      NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_ordenes_folio UNIQUE (folio),
    CONSTRAINT fk_ordenes_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    CONSTRAINT fk_ordenes_paquete FOREIGN KEY (paquete_id) REFERENCES paquetes_monedas (id),
    INDEX ix_ordenes_usuario (usuario_id, creada_en),
    INDEX ix_ordenes_fecha (estado, pagada_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 18. SESIONES DE JUEGO (tiempo de juego activo, medido por latidos)
-- ---------------------------------------------------------------------
CREATE TABLE sesiones_juego (
    id                 INT UNSIGNED NOT NULL AUTO_INCREMENT,
    usuario_id         INT UNSIGNED NOT NULL,
    token              CHAR(36)     NOT NULL,
    estado             ENUM('activa', 'cerrada') NOT NULL DEFAULT 'activa',
    iniciada_en        DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    ultimo_latido      DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    segundos_activos   INT UNSIGNED NOT NULL DEFAULT 0,
    segundos_sin_pagar INT UNSIGNED NOT NULL DEFAULT 0,
    monedas_otorgadas  INT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    CONSTRAINT uq_sesiones_juego_token UNIQUE (token),
    CONSTRAINT fk_sesiones_juego_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    INDEX ix_sesiones_juego_usuario (usuario_id, iniciada_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 19. ATRIBUTOS DE CARRERA (para las carreras simuladas de apuestas)
-- ---------------------------------------------------------------------
CREATE TABLE atributos_carrera (
    item_id     INT UNSIGNED     NOT NULL,
    velocidad   TINYINT UNSIGNED NOT NULL,
    resistencia TINYINT UNSIGNED NOT NULL,
    arranque    TINYINT UNSIGNED NOT NULL,
    PRIMARY KEY (item_id),
    CONSTRAINT fk_atributos_item FOREIGN KEY (item_id) REFERENCES items (id),
    CONSTRAINT ck_atributos CHECK (velocidad BETWEEN 1 AND 100 AND resistencia BETWEEN 1 AND 100 AND arranque BETWEEN 1 AND 100)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 20. APUESTAS (carrera simulada por el servidor o reto de tiempo propio)
-- ---------------------------------------------------------------------
CREATE TABLE apuestas (
    id           INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    folio        VARCHAR(24)   NOT NULL,
    usuario_id   INT UNSIGNED  NOT NULL,
    tipo         ENUM('carrera', 'tiempo') NOT NULL,
    monto        INT UNSIGNED  NOT NULL,
    item_id      INT UNSIGNED  NULL,
    objetivo_ms  INT UNSIGNED  NULL,
    momio        DECIMAL(5, 2) NOT NULL,
    estado       ENUM('pendiente', 'ganada', 'perdida', 'cancelada') NOT NULL DEFAULT 'pendiente',
    pago         INT UNSIGNED  NOT NULL DEFAULT 0,
    partida_id   INT UNSIGNED  NULL,
    ganador_id   INT UNSIGNED  NULL,
    resultado    VARCHAR(255)  NULL,
    creada_en    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    resuelta_en  DATETIME      NULL,
    PRIMARY KEY (id),
    CONSTRAINT uq_apuestas_folio UNIQUE (folio),
    CONSTRAINT fk_apuestas_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    CONSTRAINT fk_apuestas_item    FOREIGN KEY (item_id)    REFERENCES items (id),
    CONSTRAINT fk_apuestas_ganador FOREIGN KEY (ganador_id) REFERENCES items (id),
    CONSTRAINT fk_apuestas_partida FOREIGN KEY (partida_id) REFERENCES partidas (id),
    CONSTRAINT ck_apuestas_monto CHECK (monto BETWEEN 1 AND 100000),
    CONSTRAINT ck_apuestas_momio CHECK (momio >= 1.01),
    CONSTRAINT ck_apuestas_tipo  CHECK ((tipo = 'carrera' AND item_id IS NOT NULL) OR (tipo = 'tiempo' AND objetivo_ms IS NOT NULL)),
    INDEX ix_apuestas_usuario (usuario_id, creada_en),
    INDEX ix_apuestas_fecha (creada_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 21. PREMIOS DEL GACHAPÓN (probabilidades configurables y públicas)
-- ---------------------------------------------------------------------
CREATE TABLE gacha_premios (
    id               INT UNSIGNED      NOT NULL AUTO_INCREMENT,
    nombre           VARCHAR(60)       NOT NULL,
    rareza           ENUM('comun', 'rara', 'epica') NOT NULL,
    tipo             ENUM('item', 'monedas') NOT NULL,
    item_id          INT UNSIGNED      NULL,
    monedas          INT UNSIGNED      NULL,
    peso             SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    monedas_repetido INT UNSIGNED      NOT NULL DEFAULT 0,
    activo           TINYINT(1)        NOT NULL DEFAULT 1,
    PRIMARY KEY (id),
    CONSTRAINT fk_gacha_premios_item FOREIGN KEY (item_id) REFERENCES items (id),
    CONSTRAINT ck_gacha_premios_tipo CHECK ((tipo = 'item' AND item_id IS NOT NULL) OR (tipo = 'monedas' AND monedas > 0)),
    CONSTRAINT ck_gacha_premios_peso CHECK (peso BETWEEN 1 AND 1000)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 22. TIRADAS DEL GACHAPÓN
-- ---------------------------------------------------------------------
CREATE TABLE gacha_tiradas (
    id         INT UNSIGNED     NOT NULL AUTO_INCREMENT,
    folio      VARCHAR(24)      NOT NULL,
    usuario_id INT UNSIGNED     NOT NULL,
    cantidad   TINYINT UNSIGNED NOT NULL,
    costo      INT UNSIGNED     NOT NULL,
    creada_en  DATETIME         NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    CONSTRAINT uq_gacha_tiradas_folio UNIQUE (folio),
    CONSTRAINT fk_gacha_tiradas_usuario FOREIGN KEY (usuario_id) REFERENCES usuarios (id),
    CONSTRAINT ck_gacha_tiradas_cantidad CHECK (cantidad IN (1, 10)),
    INDEX ix_gacha_tiradas_fecha (creada_en)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- 23. RESULTADOS DE CADA TIRADA
-- ---------------------------------------------------------------------
CREATE TABLE gacha_resultados (
    id                INT UNSIGNED NOT NULL AUTO_INCREMENT,
    tirada_id         INT UNSIGNED NOT NULL,
    premio_id         INT UNSIGNED NOT NULL,
    rareza            ENUM('comun', 'rara', 'epica') NOT NULL,
    repetido          TINYINT(1)   NOT NULL DEFAULT 0,
    por_garantia      TINYINT(1)   NOT NULL DEFAULT 0,
    monedas_otorgadas INT UNSIGNED NOT NULL DEFAULT 0,
    PRIMARY KEY (id),
    CONSTRAINT fk_gacha_resultados_tirada FOREIGN KEY (tirada_id) REFERENCES gacha_tiradas (id),
    CONSTRAINT fk_gacha_resultados_premio FOREIGN KEY (premio_id) REFERENCES gacha_premios (id),
    INDEX ix_gacha_resultados_rareza (rareza)
) ENGINE=InnoDB;

-- ---------------------------------------------------------------------
-- VISTA: ranking global de jugadores (solo partidas válidas)
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW v_ranking AS
SELECT  u.id                                         AS usuario_id,
        u.username,
        p.nombre_mostrar,
        COUNT(pa.id)                                 AS partidas,
        COALESCE(SUM(pa.ganador = 'J1'), 0)          AS victorias,
        COALESCE(SUM(pa.puntaje), 0)                 AS puntaje_total,
        COALESCE(MAX(pa.puntaje), 0)                 AS mejor_puntaje,
        MIN(CASE WHEN pa.ganador = 'J1' THEN pa.duracion_ms END) AS mejor_tiempo_ms
FROM usuarios u
JOIN perfiles p        ON p.usuario_id = u.id
LEFT JOIN partidas pa  ON pa.usuario_id = u.id AND pa.estado = 'finalizada'
WHERE u.activo = 1 AND u.eliminado_en IS NULL
GROUP BY u.id, u.username, p.nombre_mostrar;
