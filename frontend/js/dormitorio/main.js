// Dormitorio: escena 3D, HUD, modo edición, tienda de muebles y colección de chibis.
// El estado (monedas, chibis, muebles y su acomodo) vive en la cuenta del jugador y se guarda con la API;
// sin sesión funciona en modo demo con localStorage (ver almacen.js).
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { CHIBIS, MUEBLES, CUARTO, articulo } from './datos.js';
import * as almacen from './almacen.js';
import { crearMueble, crearCuarto, crearRejilla } from './muebles.js';
import { cargarChibi, ALTURA } from './chibis.js';
import { Habitante, Director } from './ia.js';
import { NECESIDADES, ETIQUETAS, PERFILES } from './perfiles.js';
import { celebrarLogros, esc, toast } from '../ui.js';

const $ = id => document.getElementById(id);
const { ancho, fondo } = CUARTO;
const fmt = new Intl.NumberFormat('es-MX');
const RAREZA = { comun: 'Común', rara: 'Rara', epica: 'Épica' };
let estado = { monedas: 0, nombre: 'Dormitorio', chibis: [], inventario: {}, acomodo: [], piezas: [] };   // se carga al arrancar

// ----------------------------------------------------------------------------
// Escena
// ----------------------------------------------------------------------------
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
$('escena').appendChild(renderer.domElement);

const escena = new THREE.Scene();
escena.background = new THREE.Color('#0e0b26');
escena.fog = new THREE.Fog('#0e0b26', 26, 44);

const camara = new THREE.PerspectiveCamera(38, 1, 0.1, 100);
const VISTAS = [[7.5, 10, 11], [0.6, 12.5, 10.5], [10.5, 6.5, 6.5]];
let vista = 0;
const controles = new OrbitControls(camara, renderer.domElement);
Object.assign(controles, {
  enableDamping: true, enablePan: false, minDistance: 7, maxDistance: 20,
  minAzimuthAngle: 0.02, maxAzimuthAngle: 1.5, minPolarAngle: 0.4, maxPolarAngle: 1.15,
});
function ponerVista(i) {
  camara.position.set(...VISTAS[i]); controles.target.set(0.5, 0.4, 0.6); controles.update();
}
ponerVista(0);

const cielo = new THREE.HemisphereLight('#e9e4ff', '#3a2a6e', 1.6); escena.add(cielo);
const sol = new THREE.DirectionalLight('#fff4e6', 2.1);
sol.position.set(6, 12, 7); sol.castShadow = true;
sol.shadow.mapSize.set(2048, 2048);
Object.assign(sol.shadow.camera, { left: -9, right: 9, top: 9, bottom: -9, near: 1, far: 30 });
sol.shadow.bias = -0.0008; sol.shadow.normalBias = 0.02;
escena.add(sol);
const relleno = new THREE.PointLight('#ff3ea5', 6, 14, 1.6); relleno.position.set(-4, 2.6, -3); escena.add(relleno);

escena.add(crearCuarto(CUARTO));
const rejilla = crearRejilla(CUARTO); escena.add(rejilla);

// ----------------------------------------------------------------------------
// Mundo: cuadrícula, puntos de uso y burbujas de diálogo
// ----------------------------------------------------------------------------
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const mundo = {
  ancho, fondo, camara, escena, usos: [], muebles: [], habitantes: [], ocupadas: new Set(), director: null,
  // un punto de uso está libre si nadie lo ocupa ni ocupa otro punto exclusivo del mismo mueble
  usoLibre(u) {
    return !u.ocupada && !this.usos.some(o => o !== u && o.uid === u.uid && o.ocupada && (o.exclusivo || u.exclusivo));
  },
  libre(i, j) { return i >= 0 && j >= 0 && i < ancho && j < fondo && !this.ocupadas.has(j * ancho + i); },
  aMundo(i, j) { return { x: i - ancho / 2 + 0.5, z: j - fondo / 2 + 0.5 }; },
  aCelda(x, z) { return [clamp(Math.floor(x + ancho / 2), 0, ancho - 1), clamp(Math.floor(z + fondo / 2), 0, fondo - 1)]; },
  celdasLibres() {
    const r = [];
    for (let i = 0; i < ancho; i++) for (let j = 0; j < fondo; j++) if (this.libre(i, j)) r.push([i, j]);
    return r;
  },
  celdaLibre() { const l = this.celdasLibres(); return l[Math.floor(Math.random() * l.length)]; },
  // celda libre más cercana a un punto; si se da `cerca`, desempata hacia esa celda
  celdaJunto(x, z, cerca) {
    let mejor = null, md = Infinity;
    for (const [i, j] of this.celdasLibres()) {
      const p = this.aMundo(i, j);
      const d = Math.hypot(p.x - x, p.z - z) + (cerca ? 0.05 * Math.hypot(i - cerca[0], j - cerca[1]) : 0);
      if (d < md && Math.hypot(p.x - x, p.z - z) > 0.3) { md = d; mejor = [i, j]; }
    }
    return mejor;
  },
  decir(h, texto, seg = 2.5) {
    h.burbuja?.remove();
    const b = document.createElement('div');
    b.className = 'burbuja'; b.style.setProperty('--c', h.chibi.color);
    b.innerHTML = `<b>${esc(h.chibi.nombre)}</b>${esc(texto)}`;
    $('burbujas').appendChild(b); h.burbuja = b;
    clearTimeout(h.tBurbuja);
    h.tBurbuja = setTimeout(() => { b.classList.add('sale'); setTimeout(() => b.remove(), 300); if (h.burbuja === b) h.burbuja = null; }, seg * 1000);
  },
  // emote chibi sobre la cabeza
  emote(h, simbolo, seg = 1.8) {
    h.emoteEl?.remove();
    const e = document.createElement('div');
    e.className = 'emote'; e.textContent = simbolo;
    $('burbujas').appendChild(e); h.emoteEl = e;
    clearTimeout(h.tEmote);
    h.tEmote = setTimeout(() => { e.remove(); if (h.emoteEl === e) h.emoteEl = null; }, seg * 1000);
  },
};
const director = new Director(mundo);
mundo.director = director;

// ----------------------------------------------------------------------------
// Muebles colocados
// ----------------------------------------------------------------------------
const piezas = new Map();      // uid → { item, obj }
let pantallas = [];

const huella = it => { const { def } = articulo(it.id); return it.rot % 2 ? [def.tam[1], def.tam[0]] : [...def.tam]; };
function ubicar(p) {
  const [w, d] = huella(p.item);
  p.obj.position.set(p.item.x - ancho / 2 + w / 2, 0, p.item.z - fondo / 2 + d / 2);
  p.obj.rotation.y = p.item.rot * Math.PI / 2;
}

function valido(it) {
  const [w, d] = huella(it);
  if (it.x < 0 || it.z < 0 || it.x + w > ancho || it.z + d > fondo) return false;
  const pisable = !!articulo(it.id).def.pisable;   // (sin !! un mueble normal daba undefined y nunca chocaba)
  for (const { item: o } of piezas.values()) {
    if (o.uid === it.uid || pisable !== !!articulo(o.id).def.pisable) continue;   // alfombras solo chocan con alfombras
    const [ow, od] = huella(o);
    if (it.x < o.x + ow && o.x < it.x + w && it.z < o.z + od && o.z < it.z + d) return false;
  }
  return true;
}

function agregarPieza(item) {
  const { tipo, def, variante } = articulo(item.id);
  const obj = crearMueble(tipo, def, variante);
  obj.traverse(o => { if (o.isMesh) o.userData.uid = item.uid; });
  const p = { item, obj }; piezas.set(item.uid, p); ubicar(p); escena.add(obj);
  return p;
}
function quitarPieza(uid) {
  const p = piezas.get(uid); if (!p) return;
  escena.remove(p.obj); piezas.delete(uid);
}

function reconstruirMapa() {
  mundo.ocupadas.clear(); mundo.usos = []; mundo.muebles = []; pantallas = [];
  for (const { item, obj } of piezas.values()) {
    const { def } = articulo(item.id);
    const [w, d] = huella(item);
    if (!def.pisable) for (let i = 0; i < w; i++) for (let j = 0; j < d; j++) mundo.ocupadas.add((item.z + j) * ancho + item.x + i);
    const giro = item.rot * Math.PI / 2;
    mundo.muebles.push({ tipo: articulo(item.id).tipo, uid: item.uid, x: obj.position.x, z: obj.position.z, giro });
    for (const u of def.usos) {
      const v = new THREE.Vector3(u.pos[0], 0, u.pos[1]).applyAxisAngle(THREE.Object3D.DEFAULT_UP, giro).add(obj.position);
      mundo.usos.push({ act: u.act, x: v.x, z: v.z, rot: (u.rot || 0) + giro, alto: u.alto || 0, uid: item.uid,
        exclusivo: !!u.exclusivo, ocupada: null });
    }
    obj.traverse(o => { if (o.name === 'pantalla') pantallas.push(o); });
  }
}

function teñir(obj, color) {
  obj.traverse(o => { if (o.isMesh && o.material.emissive) o.material.emissive.set(color || '#000000'); });
}

// ----------------------------------------------------------------------------
// HUD
// ----------------------------------------------------------------------------
function comodidad() {
  let c = estado.chibis.length * 20;
  for (const { item } of piezas.values()) c += articulo(item.id).def.comodidad;
  return c;
}
function pintarHUD() {
  const c = comodidad();
  $('comodidad').textContent = fmt.format(c);
  $('nivel').textContent = 1 + Math.floor(c / 150);
  $('monedas').textContent = fmt.format(estado.monedas);
  $('nombre-dorm').textContent = estado.nombre;
  $('vacio').hidden = editando || estado.chibis.length > 0;
}
// guarda el acomodo (en la cuenta, el servidor lo valida; si lo rechaza se recarga lo que hay guardado)
function guardar() { almacen.guardarAcomodo(estado, falloAlGuardar); pintarHUD(); }
function falloAlGuardar(e) {
  toast(`No se guardó el acomodo: ${e.message}`, 'error');
  recargar();
}

// ----------------------------------------------------------------------------
// Chibis
// ----------------------------------------------------------------------------
const modelos = new Map();     // codigo → objeto cargado
const miniaturas = new Map();  // codigo → dataURL

async function prepararChibi(chibi) {
  const obj = await cargarChibi(chibi);
  modelos.set(chibi.codigo, obj);
}

const mini = { r: null, escena: new THREE.Scene(), cam: new THREE.PerspectiveCamera(26, 1, 0.1, 20) };
mini.escena.add(new THREE.HemisphereLight('#ffffff', '#6a5fb0', 2.4));
mini.cam.position.set(0, 0.78, 2.6); mini.cam.lookAt(0, 0.62, 0);
// se dibuja al abrir la colección (para entonces las texturas ya cargaron) y se guarda
function miniatura(codigo) {
  if (miniaturas.has(codigo)) return miniaturas.get(codigo);
  const obj = modelos.get(codigo); if (!obj) return null;
  mini.r ??= new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  mini.r.setSize(160, 160); mini.r.outputColorSpace = THREE.SRGBColorSpace;
  obj.esqueleto.posar('quieta', 0);
  const padre = obj.raiz.parent, { position: p, rotation: r } = obj.raiz;
  const antes = { p: p.clone(), r: r.clone() };
  p.set(0, 0, 0); r.set(0, 0, 0);
  mini.escena.add(obj.raiz); obj.raiz.updateMatrixWorld(true);
  mini.r.render(mini.escena, mini.cam);
  mini.escena.remove(obj.raiz);
  p.copy(antes.p); r.copy(antes.r); padre?.add(obj.raiz);
  const url = mini.r.domElement.toDataURL('image/png');
  miniaturas.set(codigo, url);
  return url;
}

function mudarse(codigo, saludo) {
  const chibi = CHIBIS.find(c => c.codigo === codigo), obj = modelos.get(codigo);
  if (!chibi || !obj || mundo.habitantes.some(h => h.chibi.codigo === codigo)) return;
  escena.add(obj.raiz, obj.sombra);
  const h = new Habitante(chibi, obj, mundo);
  h.colocarEn(...mundo.celdaLibre());
  mundo.habitantes.push(h);
  if (saludo) { h.ejecutar('llegar'); mundo.decir(h, saludo, 3.2); }
  crearDepuracion(h);
}

// ----------------------------------------------------------------------------
// Clic en la escena
// ----------------------------------------------------------------------------
const rayo = new THREE.Raycaster(), puntero = new THREE.Vector2();
const planoPiso = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0);
function apuntar(e) {
  const r = renderer.domElement.getBoundingClientRect();
  puntero.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
  rayo.setFromCamera(puntero, camara);
}

let fichaDe = null;
function mostrarFicha(h) {
  const f = $('ficha'), c = h.chibi;
  fichaDe = h;
  f.style.setProperty('--c', c.color);
  f.innerHTML = `<button class="btn btn-texto btn-icono cerrar" type="button" aria-label="Cerrar">✕</button>
    <h3>${esc(c.nombre)}</h3><span class="badge r-${c.rareza}">${RAREZA[c.rareza]}</span>
    <p>${esc(PERFILES[c.codigo]?.resumen || c.personalidad)}</p>
    <div class="ficha-accion" id="ficha-accion"></div>
    <div class="barras">${Object.entries(NECESIDADES).map(([k, nd]) => `
      <div class="barra" title="${nd.bueno === 'alto' ? 'Mejor alta' : 'Mejor baja'}"><span>${nd.nombre}</span>
        <i style="--b:${nd.color}"><b data-n="${k}"></b></i><em data-v="${k}"></em></div>`).join('')}</div>
    <div class="ficha-util" id="ficha-util"></div>`;
  f.hidden = false;
  f.querySelector('.cerrar').onclick = () => { f.hidden = true; fichaDe = null; };
  pintarFicha();
}
function pintarFicha() {
  const h = fichaDe;
  if (!h || $('ficha').hidden) return;
  for (const k of Object.keys(NECESIDADES)) {
    const v = Math.round(h.n[k]);
    const b = $('ficha').querySelector(`[data-n="${k}"]`); if (b) b.style.width = `${v}%`;
    const e = $('ficha').querySelector(`[data-v="${k}"]`); if (e) e.textContent = v;
  }
  const a = h.encuentro ? 'interactuar' : h.accion?.id || 'libre';
  const con = h.encuentro ? ` con ${(h.encuentro.a === h ? h.encuentro.b : h.encuentro.a).chibi.nombre}` : '';
  const ve = h.vistas.length ? h.vistas.map(o => o.chibi.nombre.split(' ')[0]).join(', ') : 'nadie';
  $('ficha-accion').textContent = `${ETIQUETAS[a] || a}${con} · ve a: ${ve}`;
  $('ficha-util').innerHTML = h.utilidades.length ? 'Última decisión: ' + h.utilidades.map((u, i) =>
    `<span class="${i ? '' : 'gana'}">${esc(ETIQUETAS[u.id] || u.id)}${u.def ? ` (${esc(u.def.id)})` : ''} ${u.puntaje.toFixed(2)}</span>`).join(' · ') : '';
}

let editando = false, arrastre = null, seleccion = null, inicio = null;

renderer.domElement.addEventListener('pointerdown', e => {
  inicio = { x: e.clientX, y: e.clientY };
  if (!editando) return;
  apuntar(e);
  const objs = [...piezas.values()].map(p => p.obj);
  const golpe = rayo.intersectObjects(objs, true)
    .sort((a, b) => (articulo(piezas.get(a.object.userData.uid).item.id).def.pisable ? 1 : 0) -
                    (articulo(piezas.get(b.object.userData.uid).item.id).def.pisable ? 1 : 0))[0];
  if (!golpe) { seleccionar(null); return; }
  const p = piezas.get(golpe.object.userData.uid);
  seleccionar(p.item.uid);
  const punto = rayo.ray.intersectPlane(planoPiso, new THREE.Vector3());
  arrastre = { p, antes: { x: p.item.x, z: p.item.z }, dx: punto ? punto.x - p.obj.position.x : 0, dz: punto ? punto.z - p.obj.position.z : 0 };
  controles.enabled = false; document.body.classList.add('arrastrando');
  renderer.domElement.setPointerCapture(e.pointerId);
});

renderer.domElement.addEventListener('pointermove', e => {
  if (!arrastre) return;
  apuntar(e);
  const punto = rayo.ray.intersectPlane(planoPiso, new THREE.Vector3()); if (!punto) return;
  const [w, d] = huella(arrastre.p.item);
  const it = arrastre.p.item;
  it.x = clamp(Math.round(punto.x - arrastre.dx + ancho / 2 - w / 2), 0, ancho - w);
  it.z = clamp(Math.round(punto.z - arrastre.dz + fondo / 2 - d / 2), 0, fondo - d);
  ubicar(arrastre.p);
  teñir(arrastre.p.obj, valido(it) ? '#0d4a2c' : '#5a0a1e');
});

renderer.domElement.addEventListener('pointerup', e => {
  const clic = inicio && Math.hypot(e.clientX - inicio.x, e.clientY - inicio.y) < 6;
  if (arrastre) {
    const { p, antes } = arrastre;
    if (!valido(p.item)) { Object.assign(p.item, antes); ubicar(p); toast('Ahí no cabe: el mueble regresó a su lugar.', 'aviso'); }
    teñir(p.obj, seleccion === p.item.uid ? '#123a4a' : null);
    arrastre = null; controles.enabled = true; document.body.classList.remove('arrastrando');
    reconstruirMapa(); guardar();
    return;
  }
  if (!clic || editando) return;
  apuntar(e);
  const h = rayo.intersectObjects(mundo.habitantes.map(x => x.obj.golpe))[0];
  const hab = h && mundo.habitantes.find(x => x.obj.golpe === h.object);
  if (hab) { hab.tocar(); mostrarFicha(hab); } else { $('ficha').hidden = true; fichaDe = null; }
});

// ----------------------------------------------------------------------------
// Modo edición
// ----------------------------------------------------------------------------
function seleccionar(uid) {
  if (seleccion && piezas.get(seleccion)) teñir(piezas.get(seleccion).obj, null);
  seleccion = uid;
  if (uid) teñir(piezas.get(uid).obj, '#123a4a');
  $('sel-acciones').hidden = !uid;
}

function colocadas(id) { return estado.acomodo.filter(a => a.id === id).length; }

function pintarBandeja() {
  const cont = $('bandeja');
  const guardadas = Object.entries(estado.inventario).filter(([id, n]) => articulo(id) && n - colocadas(id) > 0);
  cont.innerHTML = guardadas.length ? '' : '<span class="vacio">No tienes muebles guardados. Cómpralos en la Tienda o guarda uno del cuarto.</span>';
  for (const [id, n] of guardadas) {
    const { variante } = articulo(id);
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'pieza'; b.style.setProperty('--m', variante.color);
    b.innerHTML = `<div class="muestra"></div>${esc(variante.nombre)}<span class="cant">×${n - colocadas(id)}</span>`;
    b.onclick = () => colocarNueva(id);
    cont.appendChild(b);
  }
}

function colocarNueva(id) {
  const uid = almacen.piezaGuardada(estado, id);
  if (uid === null) return;
  const it = { uid, id, x: 0, z: 0, rot: 0 };
  // busca el lugar válido más cercano al centro
  const opciones = [];
  for (const rot of [0, 1]) for (let x = 0; x < ancho; x++) for (let z = 0; z < fondo; z++) opciones.push({ x, z, rot });
  opciones.sort((a, b) => Math.hypot(a.x - ancho / 2, a.z - fondo / 2) - Math.hypot(b.x - ancho / 2, b.z - fondo / 2));
  const lugar = opciones.find(o => valido({ ...it, ...o }));
  if (!lugar) { toast('No hay espacio libre para ese mueble. Guarda o mueve otro primero.', 'aviso'); return; }
  Object.assign(it, lugar);
  estado.acomodo.push(it); agregarPieza(it);
  reconstruirMapa(); guardar(); pintarBandeja(); seleccionar(uid);
}

function rotarSeleccion() {
  const p = seleccion && piezas.get(seleccion); if (!p) return;
  const antes = p.item.rot;
  p.item.rot = (p.item.rot + 1) % 4;
  if (!valido(p.item)) {
    // al girar cambia la huella: intenta recorrerlo para que quepa
    const [w, d] = huella(p.item);
    p.item.x = clamp(p.item.x, 0, ancho - w); p.item.z = clamp(p.item.z, 0, fondo - d);
    if (!valido(p.item)) { p.item.rot = antes; toast('Girado no cabe en ese lugar.', 'aviso'); }
  }
  ubicar(p); reconstruirMapa(); guardar();
}

function guardarSeleccion() {
  if (!seleccion) return;
  estado.acomodo = estado.acomodo.filter(a => a.uid !== seleccion);
  quitarPieza(seleccion); seleccionar(null);
  reconstruirMapa(); guardar(); pintarBandeja();
}

function modoEdicion(si) {
  editando = si;
  document.body.classList.toggle('editando', si);
  $('btn-editar').classList.toggle('activo', si);
  $('edicion').hidden = !si; $('ficha').hidden = true;
  document.querySelectorAll('.dorm-acciones').forEach(n => { n.hidden = si; });
  rejilla.visible = si;
  if (si) director.cancelarTodo();
  for (const h of mundo.habitantes) {
    h.obj.raiz.visible = h.obj.sombra.visible = !si;
    h.burbuja?.remove(); h.emoteEl?.remove();
    if (si) { h.soltar(); h.soltarPlato(); h.accion = null; h.estado = 'editando'; }
  }
  if (si) { cerrarPanel(); pintarBandeja(); }
  else {
    almacen.guardarAcomodoYa(estado, falloAlGuardar);
    seleccionar(null); reconstruirMapa();
    for (const h of mundo.habitantes) h.colocarEn(...mundo.celdaLibre());
  }
  pintarHUD();
}

addEventListener('keydown', e => {
  if (!editando || e.target.closest('input, textarea')) return;
  if (e.key === 'r' || e.key === 'R') rotarSeleccion();
  else if (e.key === 'Delete' || e.key === 'Backspace') guardarSeleccion();
  else if (e.key === 'Escape') seleccionar(null);
});

// ----------------------------------------------------------------------------
// Tienda y colección
// ----------------------------------------------------------------------------
let panelActual = null;
function abrirPanel(cual) {
  if (editando) modoEdicion(false);
  panelActual = cual;
  $('panel').hidden = false;
  $('btn-tienda').classList.toggle('activo', cual === 'tienda');
  $('btn-coleccion').classList.toggle('activo', cual === 'coleccion');
  pintarPanel();
}
function cerrarPanel() {
  panelActual = null; $('panel').hidden = true;
  $('btn-tienda').classList.remove('activo'); $('btn-coleccion').classList.remove('activo');
}

function pintarPanel() {
  const cuerpo = $('panel-cuerpo');
  if (panelActual === 'tienda') {
    $('panel-titulo').textContent = 'Tienda de muebles';
    cuerpo.innerHTML = Object.entries(MUEBLES).filter(([, def]) => def.variantes.some(v => v.disponible !== false)).map(([tipo, def]) => `
      <h3>${esc(def.nombre)} · comodidad +${def.comodidad}</h3>
      ${def.variantes.filter(v => v.disponible !== false).map(v => {
        const tengo = estado.inventario[v.id] || 0;
        const accion = v.precio === 0
          ? `<span class="badge">${tengo ? 'Incluido' : 'Inicial'}</span>`
          : `<span class="precio">● ${fmt.format(v.precio)}</span>
             <button class="btn btn-sm btn-primario" data-comprar="${v.id}" ${estado.monedas < v.precio ? 'disabled' : ''}>Comprar</button>`;
        return `<div class="articulo" style="--m:${v.color}"><div class="muestra"></div>
          <div><div class="nombre">${esc(v.nombre)}</div><div class="detalle">${def.tam[0]}×${def.tam[1]} celdas · Tienes ${tengo}</div></div>
          <div class="lado">${accion}</div></div>`;
      }).join('')}`).join('');
    cuerpo.querySelectorAll('[data-comprar]').forEach(b => b.onclick = () => comprarMueble(b.dataset.comprar));
  } else {
    $('panel-titulo').textContent = 'Colección de chibis';
    const visibles = CHIBIS.filter(c => c.disponible !== false || estado.chibis.includes(c.codigo));
    const tengo = visibles.filter(c => estado.chibis.includes(c.codigo)).length;
    cuerpo.innerHTML = `<p class="detalle" style="margin:0;color:var(--texto-2)">Tienes ${tengo} de ${visibles.length}. Las que consigas se mudan al dormitorio.</p>` +
      visibles.map(c => {
        const mia = estado.chibis.includes(c.codigo);
        const lado = mia ? '<span class="badge exito">En el dormitorio</span>'
          : c.origen === 'tienda'
            ? `<span class="precio">● ${fmt.format(c.precio)}</span>
               <button class="btn btn-sm btn-primario" data-chibi="${c.codigo}" ${estado.monedas < c.precio ? 'disabled' : ''}>Comprar</button>`
            : almacen.EN_CUENTA
              ? `<span class="badge info">Gachapón</span>
                 <button class="btn btn-sm btn-cian" data-chibi="${c.codigo}" title="Solo sale como premio épico del gachapón">Ir al gachapón</button>`
              : `<span class="badge info">Gachapón</span>
                 <button class="btn btn-sm btn-cian" data-chibi="${c.codigo}" title="Modo demo: en el juego sale en el gachapón">Tirada demo</button>`;
        const img = miniatura(c.codigo);
        return `<div class="articulo ${mia ? '' : 'bloqueado'}" style="--m:${c.color}">
          ${img ? `<img class="muestra" src="${img}" alt="">` : '<div class="muestra"></div>'}
          <div><div class="nombre">${mia ? esc(c.nombre) : esc(c.nombre)} <span class="badge r-${c.rareza}">${RAREZA[c.rareza]}</span></div>
            <div class="detalle">${esc(c.personalidad)}</div></div>
          <div class="lado">${lado}</div></div>`;
      }).join('');
    cuerpo.querySelectorAll('[data-chibi]').forEach(b => b.onclick = () => obtenerChibi(b.dataset.chibi));
  }
}

// Compras: en la cuenta pasan por POST /api/compras (monedas reales, folio, logros); en demo, locales
let comprando = false;
async function comprarMueble(id) {
  const { variante } = articulo(id);
  if (comprando) return;
  if (estado.monedas < variante.precio) return toast('No te alcanzan las monedas.', 'error');
  comprando = true;
  try {
    avisarCompra(await almacen.comprar(estado, 'mueble', id));
    toast(`Compraste: ${variante.nombre}. Colócalo desde el modo Editar.`, 'exito');
  } catch (e) {
    toast(e.message, 'error');
    refrescarSaldo();
  } finally {
    comprando = false;
    pintarHUD(); pintarPanel();
  }
}

async function obtenerChibi(codigo) {
  const c = CHIBIS.find(x => x.codigo === codigo);
  if (!c || estado.chibis.includes(codigo) || comprando) return;
  if (c.origen === 'gacha' && almacen.EN_CUENTA) { irAlGachapon(); return; }
  if (c.origen === 'tienda' && estado.monedas < c.precio) return toast('No te alcanzan las monedas.', 'error');
  if (c.origen === 'gacha') toast('Modo demo: en el juego esta chibi sale como premio del gachapón.', 'info');
  comprando = true;
  try {
    avisarCompra(await almacen.comprar(estado, 'chibi', codigo));
  } catch (e) {
    toast(e.message, 'error');
    refrescarSaldo();
    return;
  } finally {
    comprando = false;
    pintarHUD(); pintarPanel();
  }
  toast(`¡${c.nombre} se mudó al dormitorio!`, 'exito');
  mudarse(codigo, '¡Hola! Desde hoy vivo aquí.');
}

// la barra superior del juego muestra el saldo nuevo y celebra los logros desbloqueados
function avisarCompra({ saldo, logros }) {
  if (!almacen.EN_CUENTA) return;
  if (EMBEBIDO) parent.postMessage({ tipo: 'uma-saldo', saldo, logros }, location.origin);
  else celebrarLogros(logros);
}
function irAlGachapon() { (EMBEBIDO ? parent : window).location.href = '/gacha.html'; }

// el saldo pudo cambiar fuera del dormitorio (una carrera, un anuncio)
async function refrescarSaldo() {
  try {
    const s = await almacen.saldo();
    if (s === null || s === estado.monedas) return;
    estado.monedas = s;
    pintarHUD();
    if (panelActual) pintarPanel();
  } catch { /* informativo */ }
}

// vuelve a leer el dormitorio guardado en la cuenta (si el servidor rechazó un acomodo)
async function recargar() {
  let nuevo;
  try { nuevo = await almacen.cargar(); } catch (e) { toast(e.message, 'error'); return; }
  estado = nuevo;
  seleccionar(null);
  for (const uid of [...piezas.keys()]) quitarPieza(uid);
  for (const item of estado.acomodo) if (articulo(item.id)) agregarPieza(item);
  reconstruirMapa();
  if (editando) pintarBandeja();
  else {
    director.cancelarTodo();
    for (const h of mundo.habitantes) h.colocarEn(...mundo.celdaLibre());
  }
  pintarHUD();
}

// ----------------------------------------------------------------------------
// Botones
// ----------------------------------------------------------------------------
$('btn-editar').onclick = () => modoEdicion(!editando);
$('btn-listo').onclick = () => modoEdicion(false);
$('btn-rotar').onclick = rotarSeleccion;
$('btn-guardar-mueble').onclick = guardarSeleccion;
$('btn-tienda').onclick = () => (panelActual === 'tienda' ? cerrarPanel() : abrirPanel('tienda'));
$('btn-coleccion').onclick = () => (panelActual === 'coleccion' ? cerrarPanel() : abrirPanel('coleccion'));
$('panel-cerrar').onclick = cerrarPanel;
$('btn-vista').onclick = () => ponerVista(vista = (vista + 1) % VISTAS.length);
const VELOCIDADES = [1, 4, 12, 30];
$('reloj').onclick = () => {
  director.velocidad = VELOCIDADES[(VELOCIDADES.indexOf(director.velocidad) + 1) % VELOCIDADES.length];
  pintarReloj();
};
let depurar = false;
$('btn-ia').onclick = () => {
  depurar = !depurar;
  $('btn-ia').classList.toggle('activo', depurar);
  for (const h of mundo.habitantes) { h.depuracion.etiqueta.hidden = !depurar; h.depuracion.cono.visible = depurar; }
};
// "Reiniciar" solo existe en el modo demo: en la cuenta el dormitorio es progreso real
$('btn-reiniciar').hidden = almacen.EN_CUENTA;
$('btn-reiniciar').onclick = () => {
  if (!confirm('¿Reiniciar el dormitorio de prueba? Se pierden los muebles comprados y las chibis obtenidas en este navegador.')) return;
  estado = almacen.reiniciarDemo(); location.reload();
};

// ----------------------------------------------------------------------------
// Bucle
// ----------------------------------------------------------------------------
function ajustar() {
  renderer.setSize(innerWidth, innerHeight);
  camara.aspect = innerWidth / innerHeight; camara.updateProjectionMatrix();
}
addEventListener('resize', ajustar); ajustar();

const reloj = new THREE.Clock(), _p = new THREE.Vector3();
let t = 0;
const bucle = () => cuadro(Math.min(reloj.getDelta(), 0.05));
renderer.setAnimationLoop(bucle);
function cuadro(dt) {
  t += dt;
  if (!editando) { director.actualizar(dt); for (const h of mundo.habitantes) h.actualizar(dt); }
  iluminar();
  if ((tHUD -= dt) <= 0) { tHUD = 0.25; pintarReloj(); pintarFicha(); }
  for (const [k, s] of pantallas.entries()) s.material.color.setHSL((t * 0.05 + k * 0.3) % 1, 0.8, 0.55 + 0.05 * Math.sin(t * 7 + k));
  controles.update();
  renderer.render(escena, camara);
  // burbujas, emotes y etiquetas de depuración sobre la cabeza
  for (const h of mundo.habitantes) {
    const r = h.obj.raiz.position;
    _p.set(r.x, h.pose === 'dormir' ? h.alto + 0.9 : r.y + ALTURA + 0.2, r.z).project(camara);
    const x = `${(_p.x + 1) / 2 * innerWidth}px`, y = (1 - _p.y) / 2 * innerHeight;
    if (h.burbuja) { h.burbuja.style.left = x; h.burbuja.style.top = `${y}px`; }
    if (h.emoteEl) { h.emoteEl.style.left = x; h.emoteEl.style.top = `${y - (h.burbuja ? 58 : 4)}px`; }
    if (depurar && h.depuracion) {
      const dbg = h.depuracion;
      _p.set(r.x, 0, r.z).project(camara);   // la etiqueta va a los pies para no tapar la cara
      dbg.etiqueta.style.left = x; dbg.etiqueta.style.top = `${(1 - _p.y) / 2 * innerHeight + 6}px`;
      const a = h.encuentro ? 'interactuar' : h.accion?.id || 'libre';
      dbg.accion.textContent = ETIQUETAS[a] || a;
      for (const [k, el] of Object.entries(dbg.barras)) el.style.width = `${h.n[k]}%`;
      dbg.cono.position.set(r.x, 0.03, r.z);
      dbg.cono.rotation.y = h.obj.raiz.rotation.y;
      dbg.cono.visible = !h.dormida && !editando;
    }
  }
}

// --- día y noche ------------------------------------------------------------
const FASES = { madrugada: ['☾', 'Madrugada'], manana: ['☀', 'Mañana'], tarde: ['☀', 'Tarde'], noche: ['☾', 'Noche'] };
let tHUD = 0;
function pintarReloj() {
  const [ico, nombre] = FASES[director.fase];
  $('reloj-ico').textContent = ico;
  $('reloj-hora').textContent = director.textoHora;
  $('reloj-fase').textContent = `${nombre} · ×${director.velocidad}`;
}
const cDia = new THREE.Color('#fff4e6'), cAtardecer = new THREE.Color('#ff9a5c'), cNoche = new THREE.Color('#7f8cff');
const fondoDia = new THREE.Color('#1a1544'), fondoNoche = new THREE.Color('#07051a');
function iluminar() {
  const h = director.hora;
  const dia = Math.max(0, Math.sin((h - 6) / 13 * Math.PI));     // 0 de noche, 1 al mediodía
  const ocaso = Math.max(0, 1 - Math.abs(h - 18.5) / 1.5);        // tono naranja al atardecer
  sol.intensity = 0.35 + 1.8 * dia;
  sol.color.copy(cNoche).lerp(cDia, Math.min(1, dia * 1.6)).lerp(cAtardecer, ocaso * 0.7);
  cielo.intensity = 0.7 + 0.9 * dia;
  relleno.intensity = 6 + 6 * (1 - dia);
  escena.background.copy(fondoNoche).lerp(fondoDia, dia);
}

// --- capa de depuración de la IA (botón "IA") ---------------------------------
function crearDepuracion(h) {
  const { radio, fov } = h.p.percepcion;
  const geo = new THREE.CircleGeometry(radio, 32, -Math.PI / 2 - (fov * Math.PI / 360), fov * Math.PI / 180);
  const cono = new THREE.Mesh(geo, new THREE.MeshBasicMaterial({ color: h.chibi.color, transparent: true, opacity: 0.09, depthWrite: false }));
  cono.rotation.order = 'YXZ'; cono.rotation.x = -Math.PI / 2; cono.visible = depurar;
  escena.add(cono);
  const etiqueta = document.createElement('div');
  etiqueta.className = 'ia-etiqueta'; etiqueta.hidden = !depurar;
  etiqueta.style.setProperty('--c', h.chibi.color);
  etiqueta.innerHTML = `<strong></strong>${Object.entries(NECESIDADES).map(([k, nd]) =>
    `<i title="${nd.nombre}" style="--b:${nd.color}"><b data-n="${k}"></b></i>`).join('')}`;
  $('burbujas').appendChild(etiqueta);
  const barras = {};
  etiqueta.querySelectorAll('[data-n]').forEach(b => { barras[b.dataset.n] = b; });
  h.depuracion = { cono, etiqueta, barras, accion: etiqueta.querySelector('strong') };
}

// ----------------------------------------------------------------------------
// Dentro de la interfaz del juego (jugar.html carga dormitorio.html?embebido=1):
// el dormitorio es una sección más, junto a la carrera
// ----------------------------------------------------------------------------
const EMBEBIDO = new URLSearchParams(location.search).has('embebido') && parent !== window;
let pausado = false;
// mientras la sección no se ve no se dibuja y el reloj del dormitorio no avanza
function pausar(si) {
  if (si === pausado) return;
  pausado = si;
  if (!si) { reloj.getDelta(); refrescarSaldo(); }   // el primer cuadro al volver no cuenta el tiempo en pausa
  renderer.setAnimationLoop(si ? null : bucle);
}
if (EMBEBIDO) {
  document.body.classList.add('embebido');
  $('btn-volver').hidden = true;
  $('btn-carreras').hidden = false;
  $('btn-carreras').onclick = () => parent.postMessage({ tipo: 'uma-abrir', seccion: 'carreras' }, location.origin);
  addEventListener('message', e => {
    if (e.origin !== location.origin || e.source !== parent || e.data?.tipo !== 'uma-seccion') return;
    pausar(!e.data.visible);
  });
}

// ----------------------------------------------------------------------------
// Arranque
// ----------------------------------------------------------------------------
if (!almacen.EN_CUENTA) {
  $('monedas-etq').textContent = 'monedas de prueba';
  $('chip-monedas').title = 'Modo demo (sin sesión): monedas de prueba guardadas en este navegador';
}

(async () => {
  try {
    estado = await almacen.cargar();
  } catch (e) {
    $('carga').innerHTML = `<div class="dorm-carga-txt">No se pudo cargar tu dormitorio</div>
      <p class="dorm-carga-error">${esc(e.message)}</p><button class="btn btn-primario" type="button" id="reintentar">Reintentar</button>`;
    $('reintentar').onclick = () => location.reload();
    return;
  }
  for (const item of estado.acomodo) if (articulo(item.id)) agregarPieza(item);
  reconstruirMapa(); pintarHUD();
  const fallas = (await Promise.allSettled(CHIBIS.map(prepararChibi))).filter(r => r.status === 'rejected');
  fallas.forEach(f => console.error(f.reason));
  if (fallas.length) toast(`No se pudieron cargar ${fallas.length} chibis.`, 'error');
  for (const codigo of estado.chibis) mudarse(codigo);
  $('carga').classList.add('fuera');
  pintarReloj();
  window.__dorm = { mundo, director, estado: () => estado, piezas, controles, camara, cuadro, pausado: () => pausado };   // para depurar en consola
})();
