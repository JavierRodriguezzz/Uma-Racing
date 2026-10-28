// Cómo se ve y se comporta cada chibi y cada mueble del dormitorio.
// Con sesión, los precios y lo que está a la venta salen del catálogo de la cuenta (tipos 'chibi' y 'mueble'
// de /api/dormitorio; ver almacen.js). Los precios de aquí solo se usan en el modo demo (sin sesión).
// Cada código debe existir en la base de datos: muebles con su mismo código y chibis como chibi_<codigo>.

// ----------------------------------------------------------------------------
// Chibis coleccionables
//   origen: 'tienda' (se compra con monedas) o 'gacha' (solo sale en el gachapón; en la BD, solo_gacha = 1)
//   frases: lo que dice al tocarla. Su comportamiento (necesidades, reglas, encuentros) está en perfiles.js
// ----------------------------------------------------------------------------
export const CHIBIS = [
  {
    codigo: 'silencesuzuka', nombre: 'Silence Suzuka', rareza: 'epica', origen: 'gacha', precio: null,
    modelo: 'modelo.fbx', color: '#ff8a3d',
    personalidad: 'Introvertida, serena y muy enfocada. Corre para estar en paz y evita las multitudes.',
    frases: ['El paisaje desde el frente… quiero volver a verlo.', 'Una vuelta más.', '…', 'Hoy hace buen viento.'],
    texturas: { pelo: 'tex_mchr1002_00_hair_diff', cuerpo: 'tex_mbdy1002_00_diff', cara: 'tex_mchr0001_00_face0_1_diff',
      ojos: 'tex_mchr1002_00_eye_diff', boca: 'tex_mchr1002_00_mouth_diff', cejas: 'tex_mchr1002_00_mayu_diff',
      cola: 'tex_mtail0001_00_1002_diff', mejillas: 'face_cheek_base' },
  },
  {
    codigo: 'oguricap', nombre: 'Oguri Cap', rareza: 'rara', origen: 'tienda', precio: 400,
    modelo: 'modelo.fbx', color: '#c9cbd6',
    personalidad: 'Inocente y directa; tranquila fuera de la pista. Su apetito no tiene fondo y siempre acaba junto a Akebono.',
    frases: ['¿Ya es hora de comer?', 'Tengo hambre.', '…Akebono cocina rico.', '¿Vas a terminarte eso?'],
    texturas: { pelo: 'tex_mchr1006_00_hair_diff', cuerpo: 'tex_mbdy1006_00_diff', cara: 'tex_mchr0001_00_face0_0_diff',
      ojos: 'tex_mchr1006_00_eye_diff', boca: 'tex_mchr1006_00_mouth_diff', cejas: 'tex_mchr1006_00_mayu_diff',
      cola: 'tex_mtail0001_00_1006_diff', mejillas: 'tex_mchr0001_00_face0_0_cheek1' },
  },
  {
    codigo: 'hishiakebono', nombre: 'Hishi Akebono', rareza: 'rara', origen: 'tienda', precio: 450,
    modelo: 'modelo.fbx', color: '#ff9db8',
    personalidad: 'Maternal, alegre y protectora. Cocina y alimenta a quien se vea cansada, hambrienta o triste.',
    frases: ['¿Ya comiste? ¡Te preparo algo!', '¡A comer bien para crecer fuerte!', '¡Hoy toca chanko!'],
    texturas: { pelo: 'tex_mchr1028_01_hair_diff', cuerpo: 'tex_mbdy1028_01_diff', cara: 'tex_mchr0001_00_face0_1_diff',
      ojos: 'tex_mchr1028_01_eye_diff', boca: 'tex_mchr1028_01_mouth_diff', cejas: 'tex_mchr1028_01_mayu_diff',
      cola: 'tex_mtail0001_00_1028_diff', mejillas: 'face_cheek_base' },
  },
  {
    codigo: 'fenomeno', nombre: 'Fenomeno', rareza: 'comun', origen: 'tienda', precio: 250,
    modelo: 'modelo.fbx', color: '#7b5cff',
    personalidad: 'Disciplinada, seria y formal. Cumple horarios, patrulla y pone orden cuando alguien hace caos.',
    frases: ['Según el horario, toca entrenar.', 'Ronda de vigilancia.', 'Todo en orden por aquí.'],
    texturas: { pelo: 'tex_mchr1127_00_hair_diff', cuerpo: 'tex_mbdy1127_00_diff', cara: 'tex_mchr0001_00_face0_2_diff',
      ojos: 'tex_mchr1127_00_eye_diff', boca: 'tex_mchr1127_00_mouth_diff', cejas: 'tex_mchr1127_00_mayu_diff',
      cola: 'tex_mtail0001_00_1127_diff', mejillas: 'tex_mchr0001_00_face0_0_cheek0' },
  },
  {
    codigo: 'staygold', nombre: 'Stay Gold', rareza: 'epica', origen: 'gacha', precio: null,
    modelo: 'modelo.glb', color: '#d9b45a',
    personalidad: 'Excéntrica, rebelde e impredecible. Rompe rutinas, hace bromas y desafía a Fenomeno.',
    frases: ['¿Reglas? ¿Qué reglas?', '¡La próxima es la mía!', 'Me aburro… ¿hacemos algo raro?'],
    // GLB: trae sus texturas embebidas; solo la boca se reemplaza (la embebida perdió la transparencia)
    texturas: { boca: 'tex_mchr1135_00_mouth_diff_2' },
  },
];

// ----------------------------------------------------------------------------
// Muebles: una entrada por tipo con sus variantes (cada variante es un artículo comprable).
//   tam: [ancho, fondo] en celdas;  pisable: no bloquea el paso (alfombras)
//   tam y pisable también están en la BD (atributos_mueble): el servidor valida el acomodo con ellos,
//   así que si cambias uno aquí cámbialo en database/generar_seed.py
//   usos: dónde y cómo lo usa una chibi; pos en celdas relativas al centro, rot = hacia dónde mira
// ----------------------------------------------------------------------------
export const MUEBLES = {
  sofa: { nombre: 'Sofá', tam: [2, 1], comodidad: 60,
    usos: [{ act: 'sentarse', pos: [-0.5, 0], alto: 0.42 }, { act: 'sentarse', pos: [0.5, 0], alto: 0.42 },
           { act: 'dormir', pos: [0.62, 0.05], rot: Math.PI / 2, alto: 0.36, exclusivo: true }],
    variantes: [{ id: 'sofa_menta', nombre: 'Sofá menta', color: '#5dffb0', precio: 0 },
                { id: 'sofa_magenta', nombre: 'Sofá neón magenta', color: '#ff3ea5', precio: 180 },
                { id: 'sofa_noche', nombre: 'Sofá medianoche', color: '#4a3fa3', precio: 220 }] },
  cama: { nombre: 'Cama', tam: [2, 3], comodidad: 90,
    usos: [{ act: 'dormir', pos: [0, 0.2], alto: 0.5 }],
    variantes: [{ id: 'cama_simple', nombre: 'Cama sencilla', color: '#9a7bff', precio: 0 },
                { id: 'cama_ficha', nombre: 'Cama ficha dorada', color: '#ffd23f', precio: 300 },
                { id: 'cama_cian', nombre: 'Cama cian', color: '#38e8ff', precio: 300 }] },
  mesa: { nombre: 'Mesa baja', tam: [2, 2], comodidad: 30,
    usos: [{ act: 'comer', pos: [1.15, 0], rot: -Math.PI / 2 }, { act: 'comer', pos: [-1.15, 0], rot: Math.PI / 2 },
           { act: 'subirse', pos: [0, 0], alto: 0.4 }],   // travesura de Stay Gold
    variantes: [{ id: 'mesa_blanca', nombre: 'Mesa blanca', color: '#f1edff', precio: 0 },
                { id: 'mesa_madera', nombre: 'Mesa de madera', color: '#b07a4a', precio: 120 }] },
  refri: { nombre: 'Refrigerador', tam: [1, 1], comodidad: 25,
    usos: [{ act: 'comer', pos: [0, 0.95], rot: Math.PI, exclusivo: true }, { act: 'cocinar', pos: [0, 0.95], rot: Math.PI, exclusivo: true }],
    variantes: [{ id: 'refri_blanco', nombre: 'Refrigerador', color: '#e6e3f5', precio: 150 }] },
  tele: { nombre: 'Televisión', tam: [2, 1], comodidad: 45,
    usos: [{ act: 'tele', pos: [-1.6, 2.6], rot: Math.PI - 0.5 }, { act: 'tele', pos: [1.6, 2.6], rot: Math.PI + 0.5 }],
    variantes: [{ id: 'tele_negra', nombre: 'Televisión', color: '#211b4f', precio: 0 },
                { id: 'tele_arcade', nombre: 'Televisión retro', color: '#ff5c7a', precio: 200 }] },
  arcade: { nombre: 'Máquina arcade', tam: [1, 1], comodidad: 50,
    usos: [{ act: 'tele', pos: [0, 0.95], rot: Math.PI }],
    variantes: [{ id: 'arcade_uma', nombre: 'Arcade UmaRacing', color: '#ff3ea5', precio: 350 }] },
  caminadora: { nombre: 'Caminadora', tam: [1, 2], comodidad: 35,
    usos: [{ act: 'correr', pos: [0, 0], alto: 0.18 }],
    variantes: [{ id: 'caminadora', nombre: 'Caminadora', color: '#38e8ff', precio: 250 }] },
  puf: { nombre: 'Puf', tam: [1, 1], comodidad: 20,
    usos: [{ act: 'sentarse', pos: [0, 0], alto: 0.34 }],
    variantes: [{ id: 'puf_ficha', nombre: 'Puf amarillo', color: '#ffd23f', precio: 60 },
                { id: 'puf_menta', nombre: 'Puf menta', color: '#5dffb0', precio: 60 }] },
  planta: { nombre: 'Planta', tam: [1, 1], comodidad: 15, usos: [],
    variantes: [{ id: 'planta', nombre: 'Planta en maceta', color: '#5dffb0', precio: 40 }] },
  lampara: { nombre: 'Lámpara', tam: [1, 1], comodidad: 15, usos: [],
    variantes: [{ id: 'lampara_cian', nombre: 'Lámpara neón', color: '#38e8ff', precio: 70 }] },
  estante: { nombre: 'Estante', tam: [2, 1], comodidad: 20, usos: [],
    variantes: [{ id: 'estante_trofeos', nombre: 'Estante de trofeos', color: '#4a3fa3', precio: 160 }] },
  alfombra: { nombre: 'Alfombra', tam: [3, 3], comodidad: 25, pisable: true, usos: [],
    variantes: [{ id: 'alfombra_herradura', nombre: 'Alfombra herradura', color: '#ff3ea5', precio: 0 },
                { id: 'alfombra_pista', nombre: 'Alfombra pista', color: '#5dffb0', precio: 140 }] },
};

// Busca la variante (artículo) por id → { tipo, def, variante }
export function articulo(id) {
  for (const [tipo, def] of Object.entries(MUEBLES)) {
    const variante = def.variantes.find(v => v.id === id);
    if (variante) return { tipo, def, variante };
  }
  return null;
}

// Tamaño de la habitación en celdas
export const CUARTO = { ancho: 12, fondo: 9 };

// ----------------------------------------------------------------------------
// Modo demo (sin sesión): estado de ejemplo guardado en localStorage
// ----------------------------------------------------------------------------
const CLAVE = 'uma-dormitorio-demo-v1';

export function estadoInicial() {
  return {
    monedas: 1500,
    nombre: 'Dormitorio de Tracen',
    chibis: ['oguricap', 'silencesuzuka'],
    // inventario: id de variante → cantidad que tiene (colocadas + guardadas)
    inventario: { sofa_menta: 1, cama_simple: 1, mesa_blanca: 1, tele_negra: 1, alfombra_herradura: 1, refri_blanco: 1, planta: 2, caminadora: 1 },
    // acomodo: x,z = celda de la esquina superior izquierda; rot = 0..3 (cuartos de vuelta)
    acomodo: [
      { uid: 1, id: 'cama_simple', x: 0, z: 0, rot: 0 },
      { uid: 2, id: 'alfombra_herradura', x: 5, z: 1, rot: 0 },
      { uid: 3, id: 'sofa_menta', x: 5, z: 4, rot: 2 },
      { uid: 4, id: 'mesa_blanca', x: 5, z: 1, rot: 0 },
      { uid: 5, id: 'tele_negra', x: 5, z: 0, rot: 0 },
      { uid: 6, id: 'refri_blanco', x: 11, z: 0, rot: 0 },
      { uid: 7, id: 'planta', x: 3, z: 0, rot: 0 },
      { uid: 8, id: 'planta', x: 11, z: 8, rot: 0 },
      { uid: 9, id: 'caminadora', x: 9, z: 6, rot: 0 },
    ],
  };
}

export function cargarEstado() {
  try {
    const s = JSON.parse(localStorage.getItem(CLAVE));
    if (s && Array.isArray(s.acomodo)) return s;
  } catch { /* sin almacenamiento: estado de ejemplo */ }
  return estadoInicial();
}

export function guardarEstado(s) {
  try { localStorage.setItem(CLAVE, JSON.stringify(s)); } catch { /* el prototipo sigue sin guardar */ }
}

export function reiniciarEstado() {
  try { localStorage.removeItem(CLAVE); } catch { /* nada que borrar */ }
  return estadoInicial();
}
