-- =====================================================================
--  UmaRacing Online — Datos de prueba (generado por generar_seed.py)
--  Ejecutar DESPUÉS de schema.sql:  mysql -u root -p uma_racing < database/seed.sql
-- =====================================================================
USE uma_racing;
SET NAMES utf8mb4;

INSERT INTO roles (id, nombre, descripcion) VALUES
  (1, 'administrador', 'Gestiona tienda, anuncios, logros, usuarios y reportes.'),
  (2, 'jugador', 'Juega, compra en la tienda, mira anuncios y consulta su progreso.');

INSERT INTO tipos_item (id, codigo, nombre) VALUES (1, 'personaje', 'Personaje'), (2, 'escenario', 'Escenario');

INSERT INTO items (id, tipo_id, codigo, nombre, descripcion, precio, es_gratuito, imagen_url) VALUES
  (1, 1, 'goldship', 'Gold Ship', 'Impredecible y caótica. Personaje inicial.', 0, 1, 'img/personajes/goldship.png'),
  (2, 1, 'oguricap', 'Oguri Cap', 'La glotona de corazón enorme. Personaje inicial.', 0, 1, 'img/personajes/oguricap.png'),
  (3, 1, 'elcondorpasa', 'El Condor Pasa', 'Luchadora enmascarada con estilo propio.', 300, 0, 'img/personajes/elcondorpasa.png'),
  (4, 1, 'junglepocket', 'Jungle Pocket', 'Rival feroz que nunca se rinde.', 450, 0, 'img/personajes/junglepocket.png'),
  (5, 2, 'clasico', 'Pradera Clásica', 'El escenario original de UmaRacing.', 0, 1, 'img/escenarios/clasico.png'),
  (6, 2, 'atardecer', 'Atardecer', 'Escenario de ejemplo: la pradera al caer el sol.', 250, 0, 'img/escenarios/atardecer.png');

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
  (6, 'Jungle Pocket', 'epica', 'item', 4, NULL, 1, 250);

INSERT INTO usuarios (id, rol_id, username, email, password_hash, activo, creado_en, ultimo_acceso) VALUES
  (1, 1, 'admin', 'admin@example.com', '$2b$10$bYdSqMg58syaeS6GhgTSgOXC6Sr1aIpztIkg0H3hRl56ONuEDnRYu', 1, NOW() - INTERVAL 5616000 SECOND, NOW() - INTERVAL 3600 SECOND),
  (2, 2, 'jugador1', 'jugador1@example.com', '$2b$10$pLVngxkXudD0TugGXWl8n.0Hy8CYP/UoVN3YQalkLrUW73aEcdPei', 1, NOW() - INTERVAL 5184000 SECOND, NOW() - INTERVAL 176400 SECOND),
  (3, 2, 'jugador2', 'jugador2@example.com', '$2b$10$m.EogJwVL5AjpMPPtQXDSuoTZZP9VgDjn8lEHb0CIh8OZht83do4u', 1, NOW() - INTERVAL 172800 SECOND, NOW() - INTERVAL 3600 SECOND);

INSERT INTO perfiles (usuario_id, nombre_mostrar, biografia, monedas, personaje_favorito_id, escenario_equipado_id, tiradas_sin_epica) VALUES
  (1, 'Administrador', '', 0, NULL, NULL, 0),
  (2, 'Jugador Uno', '', 0, NULL, 5, 0),
  (3, 'Jugador Dos', '', 0, NULL, 5, 0);












