-- =====================================================================
--  UmaRacing Online — Datos de prueba (generado por generar_seed.py)
--  Ejecutar DESPUÉS de schema.sql:  mysql -u root -p uma_racing < database/seed.sql
-- =====================================================================
USE uma_racing;
SET NAMES utf8mb4;

INSERT INTO roles (id, nombre, descripcion) VALUES
  (1, 'administrador', 'Gestiona tienda, anuncios, logros, usuarios y reportes.'),
  (2, 'jugador', 'Juega, compra en la tienda, mira anuncios y consulta su progreso.');

INSERT INTO tipos_item (id, codigo, nombre) VALUES (1, 'personaje', 'Personaje'), (2, 'escenario', 'Escenario'),
  (3, 'chibi', 'Chibi'), (4, 'mueble', 'Mueble');

INSERT INTO items (id, tipo_id, codigo, nombre, descripcion, precio, es_gratuito, solo_gacha, imagen_url) VALUES
  (1, 1, 'goldship', 'Gold Ship', 'Impredecible y caótica. Personaje inicial.', 0, 1, 0, 'img/personajes/goldship.png'),
  (2, 1, 'oguricap', 'Oguri Cap', 'La glotona de corazón enorme. Personaje inicial.', 0, 1, 0, 'img/personajes/oguricap.png'),
  (3, 1, 'elcondorpasa', 'El Condor Pasa', 'Luchadora enmascarada con estilo propio.', 300, 0, 0, 'img/personajes/elcondorpasa.png'),
  (4, 1, 'junglepocket', 'Jungle Pocket', 'Rival feroz que nunca se rinde.', 450, 0, 0, 'img/personajes/junglepocket.png'),
  (5, 2, 'clasico', 'Pradera Clásica', 'El escenario original de UmaRacing.', 0, 1, 0, 'img/escenarios/clasico.png'),
  (6, 2, 'atardecer', 'Atardecer', 'Escenario de ejemplo: la pradera al caer el sol.', 250, 0, 0, 'img/escenarios/atardecer.png'),
  (7, 3, 'chibi_silencesuzuka', 'Chibi Silence Suzuka', 'Introvertida y serena; corre para estar en paz. Exclusiva del gachapón.', 0, 0, 1, 'img/chibis/silencesuzuka.png'),
  (8, 3, 'chibi_oguricap', 'Chibi Oguri Cap', 'Su apetito no tiene fondo y siempre acaba junto a Akebono.', 400, 0, 0, 'img/chibis/oguricap.png'),
  (9, 3, 'chibi_hishiakebono', 'Chibi Hishi Akebono', 'Maternal y alegre: cocina para quien se vea cansada.', 450, 0, 0, 'img/chibis/hishiakebono.png'),
  (10, 3, 'chibi_fenomeno', 'Chibi Fenomeno', 'Disciplinada y formal: patrulla y pone orden.', 250, 0, 0, 'img/chibis/fenomeno.png'),
  (11, 3, 'chibi_staygold', 'Chibi Stay Gold', 'Excéntrica y rebelde: rompe rutinas y hace bromas. Exclusiva del gachapón.', 0, 0, 1, 'img/chibis/staygold.png'),
  (12, 4, 'sofa_menta', 'Sofá menta', 'Mueble para el dormitorio (2×1 celdas).', 0, 1, 0, NULL),
  (13, 4, 'sofa_magenta', 'Sofá neón magenta', 'Mueble para el dormitorio (2×1 celdas).', 180, 0, 0, NULL),
  (14, 4, 'sofa_noche', 'Sofá medianoche', 'Mueble para el dormitorio (2×1 celdas).', 220, 0, 0, NULL),
  (15, 4, 'cama_simple', 'Cama sencilla', 'Mueble para el dormitorio (2×3 celdas).', 0, 1, 0, NULL),
  (16, 4, 'cama_ficha', 'Cama ficha dorada', 'Mueble para el dormitorio (2×3 celdas).', 300, 0, 0, NULL),
  (17, 4, 'cama_cian', 'Cama cian', 'Mueble para el dormitorio (2×3 celdas).', 300, 0, 0, NULL),
  (18, 4, 'mesa_blanca', 'Mesa blanca', 'Mueble para el dormitorio (2×2 celdas).', 0, 1, 0, NULL),
  (19, 4, 'mesa_madera', 'Mesa de madera', 'Mueble para el dormitorio (2×2 celdas).', 120, 0, 0, NULL),
  (20, 4, 'refri_blanco', 'Refrigerador', 'Mueble para el dormitorio (1×1 celdas).', 150, 0, 0, NULL),
  (21, 4, 'tele_negra', 'Televisión', 'Mueble para el dormitorio (2×1 celdas).', 0, 1, 0, NULL),
  (22, 4, 'tele_arcade', 'Televisión retro', 'Mueble para el dormitorio (2×1 celdas).', 200, 0, 0, NULL),
  (23, 4, 'arcade_uma', 'Arcade UmaRacing', 'Mueble para el dormitorio (1×1 celdas).', 350, 0, 0, NULL),
  (24, 4, 'caminadora', 'Caminadora', 'Mueble para el dormitorio (1×2 celdas).', 250, 0, 0, NULL),
  (25, 4, 'puf_ficha', 'Puf amarillo', 'Mueble para el dormitorio (1×1 celdas).', 60, 0, 0, NULL),
  (26, 4, 'puf_menta', 'Puf menta', 'Mueble para el dormitorio (1×1 celdas).', 60, 0, 0, NULL),
  (27, 4, 'planta', 'Planta en maceta', 'Mueble para el dormitorio (1×1 celdas).', 40, 0, 0, NULL),
  (28, 4, 'lampara_cian', 'Lámpara neón', 'Mueble para el dormitorio (1×1 celdas).', 70, 0, 0, NULL),
  (29, 4, 'estante_trofeos', 'Estante de trofeos', 'Mueble para el dormitorio (2×1 celdas).', 160, 0, 0, NULL),
  (30, 4, 'alfombra_herradura', 'Alfombra herradura', 'Mueble para el dormitorio (3×3 celdas).', 0, 1, 0, NULL),
  (31, 4, 'alfombra_pista', 'Alfombra pista', 'Mueble para el dormitorio (3×3 celdas).', 140, 0, 0, NULL);

INSERT INTO atributos_mueble (item_id, ancho, fondo, pisable) VALUES
  (12, 2, 1, 0),
  (13, 2, 1, 0),
  (14, 2, 1, 0),
  (15, 2, 3, 0),
  (16, 2, 3, 0),
  (17, 2, 3, 0),
  (18, 2, 2, 0),
  (19, 2, 2, 0),
  (20, 1, 1, 0),
  (21, 2, 1, 0),
  (22, 2, 1, 0),
  (23, 1, 1, 0),
  (24, 1, 2, 0),
  (25, 1, 1, 0),
  (26, 1, 1, 0),
  (27, 1, 1, 0),
  (28, 1, 1, 0),
  (29, 2, 1, 0),
  (30, 3, 3, 1),
  (31, 3, 3, 1);

INSERT INTO anuncios (id, titulo, anunciante, descripcion, color, duracion_seg, recompensa_monedas) VALUES
  (1, 'Zanahorias Turbo', 'Granja Galope S.A.', 'La zanahoria crujiente de los campeones.', '#f97316', 10, 15),
  (2, 'Bebida Sprint+', 'Bebidas Meta', 'Hidratación para la recta final.', '#06b6d4', 15, 25),
  (3, 'Herraduras Pro', 'Taller Trote', 'Agarre perfecto en cualquier pista.', '#64748b', 8, 10),
  (4, 'Academia Tracen', 'Escuela Tracen', 'Inscripciones abiertas para nuevas corredoras.', '#a855f7', 20, 40),
  (5, 'Pista Arcoíris', 'Parque Hipódromo', 'Visita el parque temático más veloz.', '#22c55e', 12, 20);

INSERT INTO logros (id, codigo, nombre, descripcion, condicion, valor_objetivo, recompensa_monedas) VALUES
  (1, 'primera_carrera', 'Primera carrera', 'Completa tu primera partida.', 'partidas_jugadas', 1, 20),
  (2, 'corredor_10', 'Corredor constante', 'Completa 10 partidas.', 'partidas_jugadas', 10, 50),
  (3, 'maratonista_50', 'Maratonista', 'Completa 50 partidas.', 'partidas_jugadas', 50, 200),
  (4, 'primera_victoria', 'Primera victoria', 'Gana una partida como Jugador 1.', 'victorias', 1, 25),
  (5, 'campeon_25', 'Campeón', 'Gana 25 partidas como Jugador 1.', 'victorias', 25, 150),
  (6, 'patrocinado', 'Patrocinado', 'Mira 5 anuncios completos.', 'anuncios_vistos', 5, 30),
  (7, 'coleccionista', 'Coleccionista', 'Compra 2 artículos en la tienda.', 'compras', 2, 100),
  (8, 'velocista', 'Velocista', 'Obtén 800 puntos o más en una sola partida.', 'puntaje_partida', 800, 75);

INSERT INTO atributos_carrera (item_id, velocidad, resistencia, arranque) VALUES
  (1, 84, 58, 40),
  (2, 79, 88, 55),
  (3, 81, 60, 78),
  (4, 80, 74, 62);

INSERT INTO paquetes_monedas (id, nombre, monedas, bonus, precio_mxn, destacado) VALUES
  (1, 'Puñado de monedas', 300, 0, 19.00, 0),
  (2, 'Bolsa de monedas', 800, 80, 49.00, 0),
  (3, 'Cofre de monedas', 1700, 300, 99.00, 1),
  (4, 'Bóveda dorada', 4500, 1000, 249.00, 0);

INSERT INTO gacha_premios (id, nombre, rareza, tipo, item_id, monedas, peso, monedas_repetido) VALUES
  (1, 'Bolsita de monedas', 'comun', 'monedas', NULL, 30, 6, 0),
  (2, 'Saco de monedas', 'comun', 'monedas', NULL, 60, 3, 0),
  (3, 'Escenario Atardecer', 'rara', 'item', 6, NULL, 2, 80),
  (4, 'Cofre de monedas', 'rara', 'monedas', NULL, 200, 3, 0),
  (5, 'El Condor Pasa', 'epica', 'item', 3, NULL, 1, 250),
  (6, 'Jungle Pocket', 'epica', 'item', 4, NULL, 1, 250),
  (7, 'Chibi Silence Suzuka', 'epica', 'item', 7, NULL, 1, 250),
  (8, 'Chibi Stay Gold', 'epica', 'item', 11, NULL, 1, 250);

INSERT INTO usuarios (id, rol_id, username, email, password_hash, activo, creado_en, ultimo_acceso) VALUES
  (1, 1, 'admin', 'admin@example.com', '$2b$10$2gY5IEPW/nrh8Z0jvkOSketq5kGokC8Fkd9wrPx88wmvBIqwBHj7W', 1, NOW() - INTERVAL 5616000 SECOND, NOW() - INTERVAL 3600 SECOND),
  (2, 2, 'jugador1', 'jugador1@example.com', '$2b$10$UrGWC0AHAzHnoDvViTD5AO.QJ36oJjElPZfzJyywXOIJq8wBPKyiq', 1, NOW() - INTERVAL 5184000 SECOND, NOW() - INTERVAL 176400 SECOND),
  (3, 2, 'jugador2', 'jugador2@example.com', '$2b$10$FC0u2Kaq1djKjleZw3WS0einzxrjo2eCBkPAXXUcInnFhDkuqVrNe', 1, NOW() - INTERVAL 172800 SECOND, NOW() - INTERVAL 3600 SECOND);

INSERT INTO perfiles (usuario_id, nombre_mostrar, biografia, monedas, personaje_favorito_id, escenario_equipado_id, tiradas_sin_epica) VALUES
  (1, 'Administrador', '', 0, NULL, NULL, 0),
  (2, 'Jugador Uno', '', 0, NULL, 5, 0),
  (3, 'Jugador Dos', '', 0, NULL, 5, 0);













