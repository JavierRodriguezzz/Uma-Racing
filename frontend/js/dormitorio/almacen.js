// Dónde vive el estado del dormitorio:
//  - Con sesión iniciada (dentro del juego, o /dormitorio.html servido por la app): en la cuenta.
//    GET /api/dormitorio trae monedas, catálogo, chibis y piezas; las compras usan POST /api/compras
//    (monedas reales, folio y logros) y el acomodo se guarda con PUT /api/dormitorio/acomodo.
//  - Sin sesión (p. ej. con `python -m http.server` para trabajar en la IA): demo en localStorage.
import { api, sesion } from '../api.js';
import { CHIBIS, MUEBLES, articulo, cargarEstado, guardarEstado, reiniciarEstado } from './datos.js';

export const EN_CUENTA = !!sesion.token();
const PREFIJO_CHIBI = 'chibi_';    // en el catálogo las chibis llevan prefijo (oguricap ya es una corredora)
let idsCatalogo = {};               // código del catálogo → item_id

// Precios y disponibilidad salen del catálogo de la cuenta; datos.js solo describe cómo se ve cada cosa
function aplicarCatalogo(catalogo) {
  const porCodigo = Object.fromEntries(catalogo.map(i => [i.codigo, i]));
  idsCatalogo = Object.fromEntries(catalogo.map(i => [i.codigo, i.id]));
  for (const def of Object.values(MUEBLES)) {
    for (const v of def.variantes) {
      const it = porCodigo[v.id];
      v.disponible = !!it;
      if (it) v.precio = it.precio;
    }
  }
  for (const c of CHIBIS) {
    const it = porCodigo[PREFIJO_CHIBI + c.codigo];
    c.disponible = !!it;
    if (!it) continue;
    c.precio = it.precio;
    c.origen = it.solo_gacha ? 'gacha' : it.es_gratuito ? 'gratis' : 'tienda';
  }
}

function aEstado(d) {
  const inventario = {};
  for (const p of d.muebles) inventario[p.codigo] = (inventario[p.codigo] || 0) + 1;
  return {
    monedas: d.monedas,
    nombre: d.nombre,
    chibis: d.chibis.map(c => c.slice(PREFIJO_CHIBI.length)),
    inventario,                                                    // código → piezas que tiene
    piezas: d.muebles.map(p => ({ uid: p.id, id: p.codigo })),     // cada pieza (colocada o guardada)
    acomodo: d.muebles.filter(p => p.x !== null).map(p => ({ uid: p.id, id: p.codigo, x: p.x, z: p.z, rot: p.rot })),
  };
}

export async function cargar() {
  if (!EN_CUENTA) return cargarEstado();
  const d = await api('GET', '/dormitorio');
  aplicarCatalogo(d.catalogo);
  return aEstado(d);
}

/** uid con el que se coloca una pieza guardada de ese mueble (null si no queda ninguna). */
export function piezaGuardada(estado, id) {
  if (!EN_CUENTA) return Math.max(0, ...estado.acomodo.map(a => a.uid)) + 1;
  const usadas = new Set(estado.acomodo.map(a => a.uid));
  return estado.piezas.find(p => p.id === id && !usadas.has(p.uid))?.uid ?? null;
}

/** Compra un mueble (id de variante) o una chibi (código). Devuelve { saldo, logros }; si falla lanza el error. */
export async function comprar(estado, tipo, codigo) {
  if (!EN_CUENTA) {
    const precio = tipo === 'mueble' ? articulo(codigo).variante.precio
      : CHIBIS.find(c => c.codigo === codigo).origen === 'tienda' ? CHIBIS.find(c => c.codigo === codigo).precio : 0;
    if (estado.monedas < precio) throw new Error('No te alcanzan las monedas.');
    estado.monedas -= precio;
    if (tipo === 'mueble') estado.inventario[codigo] = (estado.inventario[codigo] || 0) + 1;
    else estado.chibis.push(codigo);
    guardarEstado(estado);
    return { saldo: estado.monedas, logros: [] };
  }
  const itemId = idsCatalogo[tipo === 'mueble' ? codigo : PREFIJO_CHIBI + codigo];
  if (!itemId) throw new Error('Ese artículo ya no está a la venta.');
  const r = await api('POST', '/compras', { item_id: itemId });
  estado.monedas = r.saldo;
  if (tipo === 'mueble') {
    estado.inventario[codigo] = (estado.inventario[codigo] || 0) + 1;
    estado.piezas.push({ uid: r.pieza_id, id: codigo });
  } else {
    estado.chibis.push(codigo);
  }
  return { saldo: r.saldo, logros: r.logros_nuevos || [] };
}

// ---- Acomodo: en la cuenta se envía tras una pausa corta (agrupa varios movimientos seguidos)
// y los envíos van en fila para que el servidor siempre reciba el último
let tEnvio = null, fila = Promise.resolve();
export function guardarAcomodo(estado, alFallar) {
  if (!EN_CUENTA) { guardarEstado(estado); return; }
  clearTimeout(tEnvio);
  tEnvio = setTimeout(() => enviarAcomodo(estado, alFallar), 400);
}
/** Envía ya el acomodo pendiente (al salir del modo edición). */
export function guardarAcomodoYa(estado, alFallar) {
  if (!EN_CUENTA || tEnvio === null) return fila;
  clearTimeout(tEnvio);
  return enviarAcomodo(estado, alFallar);
}
function enviarAcomodo(estado, alFallar) {
  tEnvio = null;
  const piezas = estado.acomodo.map(({ uid, x, z, rot }) => ({ id: uid, x, z, rot }));
  fila = fila.then(() => api('PUT', '/dormitorio/acomodo', { piezas })).catch(e => alFallar?.(e));
  return fila;
}

/** Monedas actuales de la cuenta (pudieron cambiar en una carrera); null en modo demo. */
export async function saldo() {
  if (!EN_CUENTA) return null;
  return (await api('GET', '/auth/me')).monedas;
}

export const reiniciarDemo = reiniciarEstado;
