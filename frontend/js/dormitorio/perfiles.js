// Perfiles de IA de las chibis (Utility AI + reglas de interrupción + encuentros entre pares).
// Aquí solo hay DATOS de diseño: personalidades, necesidades, horarios, afinidades y guiones.
// El motor que los usa está en ia.js. Para ajustar a una chibi, cambia sus números aquí.

// ----------------------------------------------------------------------------
// Necesidades (0–100). `bueno` indica qué extremo es el deseable.
// ----------------------------------------------------------------------------
export const NECESIDADES = {
  energia:   { nombre: 'Energía',   bueno: 'alto', color: '#5dffb0' },
  hambre:    { nombre: 'Hambre',    bueno: 'bajo', color: '#ffd23f' },
  enfoque:   { nombre: 'Enfoque',   bueno: 'alto', color: '#38e8ff' },
  social:    { nombre: 'Social',    bueno: 'alto', color: '#ff9db8' },
  estres:    { nombre: 'Estrés',    bueno: 'bajo', color: '#ff5c7a' },
  diversion: { nombre: 'Diversión', bueno: 'alto', color: '#9a7bff' },
};

// Deriva por segundo real cuando no hace nada en particular (se multiplica por `ritmos` de cada chibi)
export const DERIVA = { energia: -0.15, hambre: 0.4, enfoque: -0.25, social: -0.3, estres: -0.12, diversion: -0.3 };

// Efecto por segundo de cada actividad sobre las necesidades (se suma a la deriva)
export const EFECTOS = {
  dormir:     { energia: 3.2, estres: -1.2, hambre: -0.15 },
  dormitar:   { energia: 1.8, estres: -0.6 },
  descansar:  { energia: 1.2, estres: -0.9 },
  comer:      { hambre: -11, energia: 0.4, estres: -0.5 },
  cocinar:    { social: 0.8, diversion: 1.2, energia: -0.3 },
  entrenar:   { enfoque: 4.5, energia: -0.7, estres: -1.1, hambre: 0.45 },
  patrullar:  { enfoque: 2.2, energia: -0.25 },
  tele:       { diversion: 3, estres: -0.6 },
  pasear:     { diversion: 0.8, estres: -0.25 },
  soledad:    { estres: -2.4, enfoque: 1.2 },
  travesura:  { diversion: 4.5, estres: -1, enfoque: -0.4 },
  charlar:    { social: 2.5, diversion: 1.2 },
  caminar:    { energia: -0.1 },
  correr:     { energia: -0.6, hambre: 0.3 },
};

// Multiplicadores de la utilidad según la hora del día (para todas)
export const HORARIO = {
  madrugada: { dormir: 3, entrenar: 0.2, patrullar: 0.2, tele: 0.3, pasear: 0.3, interactuar: 0.3, cocinar: 0.3, travesura: 0.7 },
  manana:    { entrenar: 1.5, comer: 1.15, dormir: 0.35, patrullar: 1.1 },
  tarde:     { interactuar: 1.2, tele: 1.1, cocinar: 1.2, dormir: 0.5 },
  noche:     { dormir: 1.5, tele: 1.3, entrenar: 0.6, patrullar: 0.8 },
};

export const ETIQUETAS = {
  libre: 'Pensando qué hacer', dormir: 'Durmiendo', descansar: 'Descansando', comer: 'Comiendo', comerAqui: 'Comiendo',
  pedirComida: 'Busca a Akebono', esperarComida: 'Espera su comida', cocinar: 'Cocinando', repartir: 'Reparte comida',
  entrenar: 'Entrenando', patrullar: 'Patrullando', tele: 'Viendo la tele', pasear: 'Paseando', soledad: 'Busca estar sola',
  travesura: 'Haciendo travesuras', interactuar: 'Platicando', intervenir: 'Pone orden', huir: 'Huyendo', llegar: 'Llegando',
  reaccion: 'Reacciona',
};

// ----------------------------------------------------------------------------
// Perfiles
//   inicial:    necesidades al llegar al dormitorio
//   ritmos:     multiplica la DERIVA de cada necesidad (2 = cambia el doble de rápido)
//   pesos:      multiplica la utilidad de cada acción (0 = nunca la hace)
//   rasgos:     sociable / introversion / disciplina / caos (0–1)
//   percepcion: radio en celdas y campo de visión en grados; `oido` = radio que percibe sin ver
//   horario:    multiplicadores propios por fase del día (se suman a HORARIO)
//   horaDormir: (opcional) no se va a dormir antes de esa hora salvo que esté agotada
// ----------------------------------------------------------------------------
export const PERFILES = {
  silencesuzuka: {
    resumen: 'Introvertida, serena y muy enfocada. Corre para estar en paz y evita las multitudes.',
    inicial: { energia: 80, hambre: 25, enfoque: 45, social: 70, estres: 20, diversion: 60 },
    ritmos: { social: 0.25, enfoque: 1.4, diversion: 0.5, hambre: 0.8 },
    pesos: { entrenar: 1.9, soledad: 1.7, pasear: 1.1, interactuar: 0.35, tele: 0.45, comer: 0.8, descansar: 0.8,
             dormir: 1, travesura: 0, patrullar: 0, cocinar: 0, pedirComida: 0 },
    rasgos: { sociable: 0.25, introversion: 0.9, disciplina: 0.7, caos: 0 },
    percepcion: { radio: 3.5, fov: 120, oido: 1.4 },
    horario: { manana: { entrenar: 2 }, madrugada: { entrenar: 0.5 } },
    rechazo: ['…Perdón, ahora no.', '…Voy a correr un rato.'],
  },
  hishiakebono: {
    resumen: 'Maternal, alegre y protectora. Cocina y alimenta a quien se vea cansada, hambrienta o triste.',
    inicial: { energia: 75, hambre: 35, enfoque: 50, social: 55, estres: 15, diversion: 60 },
    ritmos: { social: 1.3, enfoque: 0.6, hambre: 0.9 },
    pesos: { cocinar: 1.7, interactuar: 1.3, comer: 1, descansar: 1, entrenar: 0.55, tele: 0.9, pasear: 0.8,
             dormir: 1, travesura: 0, patrullar: 0, soledad: 0.1, pedirComida: 0 },
    rasgos: { sociable: 1, introversion: 0.1, disciplina: 0.4, caos: 0 },
    percepcion: { radio: 4.5, fov: 210, oido: 2 },
    horario: { tarde: { cocinar: 1.3 } },
    rechazo: ['¡Ahorita no puedo, tengo la olla en el fuego!'],
  },
  oguricap: {
    resumen: 'Inocente, directa y tranquila fuera de la pista. Su apetito no tiene fondo y siempre acaba junto a Akebono.',
    inicial: { energia: 70, hambre: 55, enfoque: 50, social: 60, estres: 10, diversion: 55 },
    ritmos: { hambre: 2.4, energia: 1.1, enfoque: 0.6, social: 0.6, diversion: 0.6 },
    pesos: { comer: 1.6, pedirComida: 1.5, descansar: 1.3, dormir: 1.15, entrenar: 0.7, interactuar: 0.7, tele: 0.8,
             pasear: 0.8, travesura: 0, patrullar: 0, cocinar: 0, soledad: 0.2 },
    rasgos: { sociable: 0.5, introversion: 0.5, disciplina: 0.5, caos: 0 },
    percepcion: { radio: 3.5, fov: 150, oido: 1.5, olfato: 7 },   // huele la comida desde lejos
    horario: {},
    rechazo: ['…Tengo hambre. Luego.'],
  },
  fenomeno: {
    resumen: 'Disciplinada, seria y formal. Cumple horarios, patrulla y pone orden cuando alguien hace caos.',
    inicial: { energia: 85, hambre: 30, enfoque: 60, social: 55, estres: 25, diversion: 50 },
    ritmos: { enfoque: 1.7, social: 0.7, diversion: 0.5, energia: 0.75 },
    pesos: { patrullar: 1.5, entrenar: 1.4, interactuar: 1.1, comer: 0.9, descansar: 0.7, tele: 0.4, pasear: 0.3,
             dormir: 1, travesura: 0, cocinar: 0, soledad: 0.3, pedirComida: 0 },
    rasgos: { sociable: 0.6, introversion: 0.4, disciplina: 1, caos: 0 },
    percepcion: { radio: 5.5, fov: 140, oido: 2 },
    horario: { manana: { entrenar: 1.8 }, tarde: { patrullar: 1.5 }, noche: { dormir: 1.3 } },
    horaDormir: 23,      // primero da el toque de queda
    rechazo: ['Ahora no. Estoy en horario de trabajo.'],
  },
  staygold: {
    resumen: 'Excéntrica, rebelde e impredecible. Rompe rutinas, hace bromas y desafía a Fenomeno.',
    inicial: { energia: 80, hambre: 35, enfoque: 30, social: 50, estres: 10, diversion: 40 },
    ritmos: { diversion: 1.9, enfoque: 0.4, social: 1.1 },
    pesos: { travesura: 1.6, pasear: 1.3, tele: 1.2, interactuar: 1.2, entrenar: 0.35, comer: 0.9, descansar: 0.8,
             dormir: 0.9, patrullar: 0, cocinar: 0, soledad: 0.2, pedirComida: 0 },
    rasgos: { sociable: 0.8, introversion: 0.2, disciplina: 0, caos: 1 },
    percepcion: { radio: 4, fov: 180, oido: 1.6 },
    horario: { noche: { travesura: 2, dormir: 0.5 }, madrugada: { travesura: 1.5 } },
    horaDormir: 23.75,   // noctámbula: choca con el toque de queda de Fenomeno
    rechazo: ['Nop.', '¿Y si mejor no?'],
  },
};

// Afinidad de la fila hacia la columna (-1 = choque, 1 = la adora). No es simétrica.
export const AFINIDAD = {
  silencesuzuka: { oguricap: 0.3, hishiakebono: 0.25, fenomeno: 0.15, staygold: -0.1 },
  oguricap:      { silencesuzuka: 0.3, hishiakebono: 0.95, fenomeno: 0.1, staygold: 0.2 },
  hishiakebono:  { silencesuzuka: 0.6, oguricap: 0.9, fenomeno: 0.5, staygold: 0.5 },
  fenomeno:      { silencesuzuka: 0.45, oguricap: 0.2, hishiakebono: 0.4, staygold: -0.6 },
  staygold:      { silencesuzuka: 0.75, oguricap: 0.3, hishiakebono: 0.25, fenomeno: -0.4 },
};
export const afinidad = (a, b) => AFINIDAD[a]?.[b] ?? 0;

// Fenomeno puede mandar a dormir a quien siga despierta (y no se lo haya dicho hace poco)
export const despiertaParaToque = (h, o, d) => !o.dormida && !o.encuentro && o.accion?.id !== 'dormir' &&
  !d.enfriado(INTERACCIONES.find(i => i.id === 'toque_queda'), h, o);

// Qué tanto necesita que la cuiden (lo usa Akebono): 0–1
export const necesitaCuidado = h => Math.max(h.n.hambre / 100, 1 - h.n.energia / 100, h.n.estres / 100);

// ----------------------------------------------------------------------------
// Reglas de interrupción: se revisan cada 0.3 s; si la prioridad supera a la de la acción
// actual, la chibi deja lo que hace. Prioridades de acciones: normal 2, comer 4, encuentro 5, dormir 6.
// ----------------------------------------------------------------------------
export const REGLAS = [
  { id: 'hambre_oguri', quien: 'oguricap', prioridad: 9,
    si: h => h.n.hambre > 80 && !['comer', 'comerAqui', 'pedirComida', 'esperarComida'].includes(h.accion?.id),
    hacer: 'pedirComida', texto: h => (h.dormida ? '…Huele a comida.' : 'Tengo… mucha hambre.'), emote: '🍙' },
  { id: 'agotada', quien: '*', prioridad: 8,
    si: h => h.n.energia < 12 && !['dormir', 'dormitar'].includes(h.accion?.id),
    hacer: 'dormir', texto: () => 'Estoy agotada…', emote: '💧' },
  { id: 'multitud', quien: 'silencesuzuka', prioridad: 7,
    si: h => h.cerca(2.5).length >= 2 && h.n.estres > 30 && !['soledad', 'entrenar'].includes(h.accion?.id),
    hacer: 'soledad', texto: () => '…Hay mucha gente. Voy a tomar aire.', emote: '💧', efecto: { estres: 15 } },
  { id: 'caos', quien: 'fenomeno', prioridad: 7,
    si: h => h.vistas.some(o => o.caos && !o.encuentro) && h.accion?.id !== 'intervenir',
    hacer: 'intervenir', emote: '❗' },
  { id: 'toque_queda', quien: 'fenomeno', prioridad: 6,
    si: (h, d) => d.hora >= 22 && d.hora < 23.9 && h.accion?.id !== 'interactuar' && h.vistas.some(o => despiertaParaToque(h, o, d)),
    hacer: 'toqueQueda', emote: '❗' },
  { id: 'cuidar', quien: 'hishiakebono', prioridad: 5,
    si: h => !h.plato && h.vistas.some(o => necesitaCuidado(o) > 0.72 && !o.dormida) &&
             !['cocinar', 'repartir', 'interactuar'].includes(h.accion?.id),
    hacer: 'cocinar', texto: () => '¡Alguien necesita comer bien!', emote: '❤' },
];

// ----------------------------------------------------------------------------
// Conversaciones casuales (encuentro "charlar"): [quién habla según `entre`, texto]
// ----------------------------------------------------------------------------
export const CHARLAS = [
  { entre: ['silencesuzuka', 'oguricap'], dialogo: [[0, '¿Corremos un rato, Oguri?'], [1, 'Después de comer.']] },
  { entre: ['silencesuzuka', 'fenomeno'], dialogo: [[1, 'Tu ritmo de ayer fue impecable.'], [0, '…Gracias. Quiero ir más rápido.']] },
  { entre: ['hishiakebono', 'oguricap'], dialogo: [[0, '¡Oguri! ¿Ya comiste?'], [1, 'Sí.'], [1, '…¿Hay más?']] },
  { entre: ['hishiakebono', 'oguricap'], dialogo: [[0, '¡Comes casi tanto como yo!'], [1, 'Casi.']] },
  { entre: ['hishiakebono', 'silencesuzuka'], dialogo: [[0, 'Suzuka, ¿dormiste bien? Te ves cansada.'], [1, '…Estoy bien. Gracias.']] },
  { entre: ['hishiakebono', 'fenomeno'], dialogo: [[1, 'La cena es a las 19:00.'], [0, '¡Y el postre a las 19:05!']] },
  { entre: ['fenomeno', 'oguricap'], dialogo: [[0, 'Oguri, ¿cuántas comidas llevas hoy?'], [1, '…¿Cuenta el desayuno doble?']] },
  { entre: ['staygold', 'oguricap'], dialogo: [[0, 'Oguri, ¿me das un poquito?'], [1, 'No.']] },
  { entre: ['staygold', 'hishiakebono'], dialogo: [[0, '¡Akebono! ¿Qué hay de cenar?'], [1, '¡Sorpresa! …Es chanko.']] },
  { entre: ['staygold', 'fenomeno'], dialogo: [[1, 'Stay Gold, ¿y tus goggles?'], [0, '¡Los dejé por… algún lado!']] },
  { entre: null, dialogo: [[0, '¡Hola!'], [1, '¡Hola, hola!']] },
  { entre: null, dialogo: [[0, '¿Entrenaste hoy?'], [1, 'Un poco.']] },
  { entre: null, dialogo: [[0, 'Qué buen día.'], [1, 'Sí, ¿verdad?']] },
];

// ----------------------------------------------------------------------------
// Encuentros (interacciones agente a agente)
//   de / a:     quién inicia y con quién ('*' = cualquiera)
//   alcance:    'vista' = solo si la iniciadora la percibe; 'todas' = sabe dónde está (horarios, búsquedas)
//   forzada:    la otra no puede rechazarla
//   cadena:     solo se dispara desde otra acción (no compite en la utilidad)
//   utilidad:   (a, b, d) → 0..1   (d = director: hora, fase, diurno)
//   guion:      (a, b, d) → { lineas: [[0|1, texto, pose, emote]], efectos: {0: {...}, 1: {...}}, despues: {0, 1} }
// ----------------------------------------------------------------------------
const azar = p => Math.random() < p;
const de = (lista) => lista[Math.floor(Math.random() * lista.length)];

export const INTERACCIONES = [
  { id: 'charlar', de: '*', a: '*', alcance: 'vista', enfriamiento: 25,
    utilidad: (a, b) => (1 - a.n.social / 100) * a.p.rasgos.sociable * (0.55 + 0.45 * afinidad(a.codigo, b.codigo)),
    guion: (a, b) => {
      const propias = CHARLAS.filter(c => c.entre?.includes(a.codigo) && c.entre?.includes(b.codigo));
      const c = propias.length && azar(0.75) ? de(propias) : de(CHARLAS.filter(x => !x.entre));
      const quien = c.entre ? c.entre.map(cod => (cod === a.codigo ? 0 : 1)) : [0, 1];
      const roce = afinidad(a.codigo, b.codigo) < 0 || afinidad(b.codigo, a.codigo) < 0;
      return { lineas: c.dialogo.map(([n, t]) => [quien[n], t, 'charlar']),
        efectos: { 0: { social: 25, diversion: 8, estres: roce ? 8 : -6 }, 1: { social: 22, diversion: 6, estres: roce ? 8 : -6 } } };
    } },

  // ---- Fenomeno: horarios, orden y deber ----
  { id: 'orden_entrenar', de: 'fenomeno', a: 'staygold', alcance: 'todas', forzada: true, enfriamiento: 45,
    utilidad: (a, b, d) => (d.diurno && b.n.enfoque < 60 && !b.dormida ? 0.5 + (60 - b.n.enfoque) / 80 : 0),
    guion: () => azar(0.7)
      ? { lineas: [[0, 'Stay Gold. Hora de entrenar.', 'senalar'], [1, 'Nop.', 'cruzada', '💢'],
                   [0, '¡Es una orden!', 'senalar', '💢'], [1, '¡Atrápame primero! ♪', 'feliz', '♪']],
          efectos: { 0: { estres: 18 }, 1: { diversion: 25 } }, despues: { 1: 'huir' } }
      : { lineas: [[0, 'Stay Gold. Hora de entrenar.', 'senalar'], [1, '…Está bien, está bien.', 'cansada', '💧']],
          efectos: { 0: { estres: -10, enfoque: 8 }, 1: { diversion: -10 } }, despues: { 1: 'entrenar' } } },

  { id: 'recordar_deber', de: 'fenomeno', a: '*', alcance: 'vista', enfriamiento: 60,
    utilidad: (a, b, d) => (b.codigo !== 'staygold' && d.diurno && b.n.enfoque < 35 &&
      ['tele', 'descansar', 'pasear'].includes(b.accion?.id) ? 0.6 : 0),
    guion: (a, b) => ({
      silencesuzuka: { lineas: [[0, 'Suzuka, ¿y tu entrenamiento de hoy?', 'senalar'], [1, 'Ya corrí… tres veces.', 'quieta'], [0, '…Bien hecho.', 'quieta']],
        efectos: { 0: { estres: -5 }, 1: { enfoque: 10 } } },
      oguricap: { lineas: [[0, 'Oguri, ¿ya entrenaste?', 'senalar'], [1, 'Después de comer.', 'quieta'], [0, 'Siempre dices eso.', 'cansada', '💧']],
        efectos: { 0: { estres: 6 } }, despues: { 1: 'comer' } },
      hishiakebono: { lineas: [[0, 'Akebono, el horario dice entrenamiento.', 'senalar'], [1, '¡Primero hay que comer bien!', 'feliz', '❤'], [0, '…El horario no dice eso.', 'cansada']],
        efectos: { 0: { estres: 6 } }, despues: { 1: 'cocinar' } },
    })[b.codigo] || { lineas: [[0, '¿Ya cumpliste tus tareas?', 'senalar'], [1, '¡Ya voy!', 'sorpresa']], despues: { 1: 'entrenar' } } },

  { id: 'regano', de: 'fenomeno', a: '*', alcance: 'vista', forzada: true, cadena: true, enfriamiento: 12,
    guion: (a, b, d) => {
      const motivo = b.accion?.id === 'travesura' && b.accion.subida ? '¡Bájate de la mesa!'
        : b.accion?.id === 'travesura' || b.caosHasta > d.tiempo ? '¡Nada de bromas en el dormitorio!'
        : 'No se corre dentro del dormitorio.';
      if (b.codigo === 'staygold') return azar(0.65)
        ? { lineas: [[0, motivo, 'senalar', '💢'], [1, '¿Yo? ¿Qué hice?', 'cruzada'], [0, '¡Ahora mismo, Stay Gold!', 'senalar', '💢'], [1, '¡Atrápame si puedes! ♪', 'feliz', '♪']],
            efectos: { 0: { estres: 20 }, 1: { diversion: 30 } }, despues: { 1: 'huir' } }
        : { lineas: [[0, motivo, 'senalar', '💢'], [1, 'Aburrido… está bien.', 'cansada', '💧']],
            efectos: { 0: { estres: -8, enfoque: 10 }, 1: { diversion: -15 } }, despues: { 1: 'descansar' } };
      return { lineas: [[0, motivo, 'senalar'], [1, '¡Perdón!', 'sorpresa', '💧']], efectos: { 1: { estres: 10 } }, despues: { 1: 'descansar' } };
    } },

  { id: 'toque_queda', de: 'fenomeno', a: '*', alcance: 'todas', forzada: true, enfriamiento: 120,
    utilidad: (a, b, d) => ((d.hora >= 22 || d.hora < 5) && !b.dormida && b.accion?.id !== 'dormir' ? 0.95 : 0),
    guion: (a, b) => ({
      staygold: { lineas: [[0, 'Son más de las diez. A dormir.', 'senalar'], [1, 'La noche es joven ♪', 'feliz', '♪'], [0, '…Stay Gold.', 'cansada', '💢']],
        efectos: { 0: { estres: 12 }, 1: { diversion: 12 } } },
      oguricap: { lineas: [[0, 'Son más de las diez. A dormir.', 'senalar'], [1, '¿Puedo cenar primero?', 'quieta', '🍙'], [0, '…Rápido.', 'cansada']],
        despues: { 1: 'comer' } },
    })[b.codigo] || { lineas: [[0, 'Son más de las diez. A dormir.', 'senalar'], [1, 'Sí, ya voy.', 'cansada']], despues: { 1: 'dormir' } } },

  { id: 'despertar', de: 'fenomeno', a: '*', alcance: 'todas', forzada: true, despierta: true, enfriamiento: 240,
    utilidad: (a, b, d) => (b.dormida && d.hora >= 7.5 && d.hora < 10 ? 0.85 : 0),
    guion: (a, b) => ({
      staygold: { lineas: [[0, 'Ya amaneció. ¡Arriba!', 'senalar'], [1, 'Cinco minutitos más…', null, '💤'], [0, '…', 'cansada', '💢']],
        efectos: { 0: { estres: 10 } } },
      oguricap: { lineas: [[0, 'Ya amaneció. ¡Arriba!', 'senalar'], [1, '…¿Ya está el desayuno?', null, '🍙']], despues: { 1: 'comer' } },
    })[b.codigo] || { lineas: [[0, 'Ya amaneció. ¡Arriba!', 'senalar'], [1, '…Buenos días.', null, '💤']], despues: { 1: 'levantarse' } } },

  // ---- Hishi Akebono: alimentar y cuidar ----
  { id: 'ofrecer_comida', de: 'hishiakebono', a: '*', alcance: 'todas', forzada: true, cadena: true, enfriamiento: 45,
    guion: (a, b) => ({
      oguricap: { lineas: [[0, '¡Recién hecho! Come mucho.', 'ofrecer', '❤'], [1, '…¡Gracias!', 'feliz', '✨'], [1, '*ñam ñam ñam*', 'comer']],
        efectos: { 0: { social: 25, diversion: 15 }, 1: { hambre: -85, energia: 15, estres: -10 } }, despues: { 1: 'comerAqui' } },
      silencesuzuka: de([
        { lineas: [[0, 'Suzuka, come algo. Estás muy delgada.', 'ofrecer'], [1, 'Gracias… lo como después.', 'quieta', '💧']],
          efectos: { 0: { social: 10 }, 1: { hambre: -25, estres: -10 } } },
        { lineas: [[0, '¡Corriste mucho hoy! Toma, repón energía.', 'ofrecer', '❤'], [1, '…Solo un poquito. Gracias.', 'comer']],
          efectos: { 0: { social: 12 }, 1: { hambre: -35, energia: 10 } } },
        { lineas: [[0, 'Suzuka, te guardé esto.', 'ofrecer'], [1, '…Lo llevo a la ventana.', 'quieta']],
          efectos: { 0: { social: 8 }, 1: { hambre: -30, estres: -8 } }, despues: { 1: 'soledad' } },
      ]),
      fenomeno: { lineas: [[0, 'Toma, para que rindas en tu horario.', 'ofrecer'], [1, '…Gracias. Anotado.', 'quieta']],
        efectos: { 0: { social: 15 }, 1: { hambre: -50, estres: -18 } }, despues: { 1: 'comerAqui' } },
      staygold: { lineas: [[0, '¡Toma, Stay Gold!', 'ofrecer'], [1, '¿Tiene picante? …Bueno, va.', 'cruzada'], [1, '…Está bueno.', 'feliz', '♪']],
        efectos: { 0: { social: 15 }, 1: { hambre: -50, diversion: 10 } }, despues: { 1: 'comerAqui' } },
    })[b.codigo] },

  { id: 'calmar', de: 'hishiakebono', a: 'fenomeno', alcance: 'vista', enfriamiento: 50,
    utilidad: (a, b) => (b.n.estres > 60 ? 0.5 + b.n.estres / 200 : 0),
    guion: () => ({ lineas: [[0, 'Fenomeno, relájate un poquito.', 'ofrecer', '❤'], [1, '…Mi horario no incluye relajarme.', 'cruzada'],
                             [0, '¡Entonces lo agregamos!', 'feliz', '♪'], [1, '…Cinco minutos.', 'quieta']],
      efectos: { 0: { social: 15 }, 1: { estres: -35 } }, despues: { 1: 'descansar' } }) },

  // ---- Oguri Cap: atraída por Akebono y la comida ----
  { id: 'pedir_comida', de: 'oguricap', a: 'hishiakebono', alcance: 'todas', forzada: true, cadena: true, enfriamiento: 20,
    guion: () => ({ lineas: [[0, 'Akebono… ¿hay algo de comer?', 'quieta', '🍙'], [1, '¡Siempre! Espérame tantito.', 'feliz', '❤']],
      efectos: { 1: { social: 10 } }, despues: { 0: 'esperarComida', 1: 'cocinar' } }) },

  // ---- Stay Gold: rarezas con Suzuka y bromas ----
  { id: 'rara', de: 'staygold', a: 'silencesuzuka', alcance: 'vista', forzada: true, enfriamiento: 40,
    utilidad: (a, b) => (b.dormida ? 0 : (1 - a.n.diversion / 100) * 0.8 + 0.2),
    guion: () => de([
      { lineas: [[0, 'Suzuka, ¿por qué siempre giras a la izquierda?', 'charlar'], [1, '…No lo sé. Se siente bien.', 'quieta'],
                 [0, '¡Hoy corremos al revés!', 'feliz', '♪'], [1, '…¿Al revés?', 'sorpresa', '💧']],
        efectos: { 0: { diversion: 30 }, 1: { estres: 10, social: 10 } }, despues: { 0: 'entrenar', 1: 'entrenar' } },
      { lineas: [[0, '¿Una carrera hasta la ventana?', 'feliz'], [1, '…Está bien. Pero yo voy al frente.', 'quieta']],
        efectos: { 0: { diversion: 20 }, 1: { social: 8 } }, despues: { 0: 'entrenar', 1: 'entrenar' } },
      { lineas: [[0, 'Suzuka, si fueras un pastel, ¿de qué serías?', 'charlar'], [1, '……¿Qué?', 'sorpresa', '❓']],
        efectos: { 0: { diversion: 25 }, 1: { estres: 8 } } },
    ]) },

  { id: 'broma', de: 'staygold', a: '*', alcance: 'vista', forzada: true, enfriamiento: 35, caos: 8,
    utilidad: (a, b) => (1 - a.n.diversion / 100) * 0.85 * (b.codigo === 'fenomeno' ? 1.25 : 1) * (b.dormida ? 0.6 : 1),
    guion: (a, b) => ({
      fenomeno: { lineas: [[0, '¡Bu!', 'feliz'], [1, '…', 'cruzada', '💢'], [1, 'Stay Gold. Tres vueltas extra.', 'senalar', '💢']],
        efectos: { 0: { diversion: 35 }, 1: { estres: 20 } }, despues: { 0: 'huir' } },
      oguricap: { lineas: [[0, '¡Bu!', 'feliz'], [1, '…¿Hola?', 'quieta'], [0, 'Ni se inmutó…', 'cansada', '💧']],
        efectos: { 0: { diversion: 8 } } },
      silencesuzuka: { lineas: [[0, '¡Bu!', 'feliz'], [1, '…¡!', 'sorpresa', '❗']],
        efectos: { 0: { diversion: 30 }, 1: { estres: 15 } }, despues: { 1: 'soledad' } },
      hishiakebono: { lineas: [[0, '¡Bu!', 'feliz'], [1, '¡Ay, qué susto! …¿Tienes hambre?', 'sorpresa', '❗']],
        efectos: { 0: { diversion: 20, hambre: -20 }, 1: { estres: 5 } } },
    })[b.codigo] },
];
