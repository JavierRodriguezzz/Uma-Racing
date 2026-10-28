// Motor de IA del dormitorio.
//
//   Director   reloj día/noche, percepción (radio + campo de visión), reglas de interrupción,
//              encuentros entre pares y la comida servida en la mesa.
//   Habitante  una chibi: necesidades que cambian con el tiempo, Utility AI para elegir la
//              siguiente acción, y la ejecución de esa acción (caminar con A*, usar muebles…).
//   Encuentro  interacción entre dos chibis: acercarse → guion (líneas, poses, emotes) →
//              efectos en sus necesidades → la acción que sigue para cada una.
//
// Bucle de vida de cada chibi:  llegar → libre (evalúa utilidades) → ejecutar acción → libre …
// y en cualquier momento una regla de mayor prioridad (o un encuentro) puede interrumpirla.
// Los datos de diseño (personalidades, reglas, guiones) están en perfiles.js.
import * as THREE from 'three';
import { toon } from './muebles.js';
import {
  PERFILES, DERIVA, EFECTOS, HORARIO, REGLAS, INTERACCIONES, afinidad, necesitaCuidado, despiertaParaToque,
} from './perfiles.js';

const VEL = { caminar: 1.25, correr: 2.6 };
const azar = (a, b) => a + Math.random() * (b - a);
const elegir = arr => arr[Math.floor(Math.random() * arr.length)];
const lim = (v, a = 0, b = 100) => Math.max(a, Math.min(b, v));
const inv = x => 1 - x / 100;
const cuad = x => x * x;
const PRIORIDAD = { dormir: 6, interactuar: 5, intervenir: 5, repartir: 5, comer: 4, comerAqui: 4, pedirComida: 4,
  esperarComida: 4, cocinar: 4, huir: 3, reaccion: 3, llegar: 3 };
const interaccion = id => INTERACCIONES.find(i => i.id === id);

// ----------------------------------------------------------------------------
// Rutas en la cuadrícula (A* con 8 vecinos, sin cortar esquinas)
// ----------------------------------------------------------------------------
export function ruta(mapa, desde, hasta) {
  const { ancho, fondo } = mapa;
  const clave = (i, j) => j * ancho + i;
  const abiertos = [[desde[0], desde[1]]], g = new Map([[clave(...desde), 0]]), previo = new Map();
  const h = (i, j) => Math.hypot(i - hasta[0], j - hasta[1]);
  const f = new Map([[clave(...desde), h(...desde)]]);
  const vistos = new Set();
  while (abiertos.length) {
    abiertos.sort((a, b) => f.get(clave(...a)) - f.get(clave(...b)));
    const [i, j] = abiertos.shift();
    const k = clave(i, j);
    if (i === hasta[0] && j === hasta[1]) {
      const camino = [[i, j]];
      let p = k; while (previo.has(p)) { p = previo.get(p); camino.unshift([p % ancho, Math.floor(p / ancho)]); }
      return camino;
    }
    vistos.add(k);
    for (const [di, dj] of [[1, 0], [-1, 0], [0, 1], [0, -1], [1, 1], [1, -1], [-1, 1], [-1, -1]]) {
      const ni = i + di, nj = j + dj, nk = clave(ni, nj);
      if (ni < 0 || nj < 0 || ni >= ancho || nj >= fondo || vistos.has(nk) || !mapa.libre(ni, nj)) continue;
      if (di && dj && (!mapa.libre(i + di, j) || !mapa.libre(i, j + dj))) continue;
      const ng = g.get(k) + (di && dj ? 1.414 : 1);
      if (ng < (g.get(nk) ?? Infinity)) {
        g.set(nk, ng); f.set(nk, ng + h(ni, nj)); previo.set(nk, k);
        if (!abiertos.some(([a, b]) => a === ni && b === nj)) abiertos.push([ni, nj]);
      }
    }
  }
  return null;
}

function crearPlato() {
  const g = new THREE.Group();
  const tazon = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.09, 0.08, 16), toon('#ffffff'));
  const comida = new THREE.Mesh(new THREE.SphereGeometry(0.11, 14, 8, 0, Math.PI * 2, 0, Math.PI / 2), toon('#ff9a3d'));
  comida.position.y = 0.035; tazon.position.y = 0.04; comida.position.y = 0.075;
  g.add(tazon, comida);
  return g;
}

// ============================================================================
// Director
// ============================================================================
export class Director {
  constructor(mundo) {
    this.mundo = mundo;
    this.minutos = 7 * 60 + 30;      // empieza a las 07:30
    this.velocidad = 4;              // minutos del juego por segundo real (un día ≈ 6 min)
    this.tiempo = 0;                 // segundos reales simulados
    this.tSensor = 0;
    this.encuentros = new Set();
    this.enfriamientos = new Map();
    this.platos = [];                // comida servida en la mesa: { mesh, uid }
  }

  get hora() { return this.minutos / 60; }
  get fase() { const h = this.hora; return h < 6 ? 'madrugada' : h < 12 ? 'manana' : h < 19 ? 'tarde' : 'noche'; }
  get diurno() { const h = this.hora; return h >= 7 && h < 21.5; }
  get textoHora() {
    const m = Math.floor(this.minutos);
    return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
  }

  actualizar(dt) {
    this.tiempo += dt;
    this.minutos = (this.minutos + dt * this.velocidad) % 1440;
    if ((this.tSensor -= dt) <= 0) { this.tSensor = 0.3; this.percibir(); this.revisarReglas(); }
    for (const e of [...this.encuentros]) e.actualizar(dt);
  }

  // Sensores: cada chibi ve a las demás dentro de su radio y su campo de visión, y "oye" a las muy cercanas
  percibir() {
    const todas = this.mundo.habitantes;
    for (const h of todas) {
      if (h.dormida || h.estado === 'editando') { h.vistas = []; continue; }
      const { radio, fov, oido } = h.p.percepcion, yaw = h.obj.raiz.rotation.y;
      h.vistas = todas.filter(o => {
        if (o === h || o.estado === 'editando') return false;
        const dx = o.pos.x - h.pos.x, dz = o.pos.z - h.pos.z, d = Math.hypot(dx, dz);
        if (d <= oido) return true;
        if (d > radio) return false;
        let ang = Math.atan2(dx, dz) - yaw;
        ang = Math.atan2(Math.sin(ang), Math.cos(ang));
        return Math.abs(ang) * 180 / Math.PI <= fov / 2;
      });
    }
  }

  // Reglas de interrupción: solo ganan si su prioridad supera a la de la acción actual
  revisarReglas() {
    for (const h of this.mundo.habitantes) {
      if (h.encuentro || h.estado === 'editando' || h.enfriaRegla > this.tiempo) continue;
      for (const r of REGLAS) {
        if ((r.quien !== '*' && r.quien !== h.codigo) || r.prioridad <= h.prioridad || !r.si(h, this)) continue;
        h.enfriaRegla = this.tiempo + 6;
        h.interrumpir(r);
        break;
      }
    }
  }

  enfriado(def, a, b) { return (this.enfriamientos.get(`${def.id}|${a.codigo}|${b.codigo}`) ?? -Infinity) > this.tiempo; }
  enfriar(def, a, b) { this.enfriamientos.set(`${def.id}|${a.codigo}|${b.codigo}`, this.tiempo + (def.enfriamiento ?? 20)); }

  iniciarEncuentro(a, b, def) {
    if (!def || !b || a === b || a.encuentro || b.encuentro || b.estado === 'editando') return null;
    const guion = def.guion(a, b, this);
    if (!guion) return null;
    this.enfriar(def, a, b);
    if (!def.forzada && !b.acepta(a)) {
      this.mundo.decir(b, elegir(b.p.rechazo), 2.2);
      this.mundo.emote(b, '💧');
      a.sumar({ estres: 5, social: -5 });
      if (b.p.rasgos.introversion > 0.7) b.ejecutar('soledad');
      return null;
    }
    const e = new Encuentro(this, a, b, def, guion);
    e.empezar();
    return e;
  }

  // --- comida servida ---------------------------------------------------------
  dejarPlato(plato) {
    const mesa = this.mundo.muebles.find(m => m.tipo === 'mesa');
    if (!mesa || this.platos.length >= 2) { plato.parent?.remove(plato); return false; }
    plato.parent?.remove(plato);
    plato.position.set(mesa.x + (this.platos.length ? 0.35 : -0.1), 0.4, mesa.z + 0.25);
    this.mundo.escena.add(plato);
    this.platos.push({ mesh: plato, uid: mesa.uid });
    return true;
  }
  tomarPlato(uid) {
    const i = this.platos.findIndex(p => p.uid === uid);
    if (i < 0) return false;
    this.platos[i].mesh.parent?.remove(this.platos[i].mesh);
    this.platos.splice(i, 1);
    return true;
  }

  // al entrar al modo edición (los muebles pueden moverse)
  cancelarTodo() {
    for (const e of [...this.encuentros]) e.liberar();
    for (const p of this.platos) p.mesh.parent?.remove(p.mesh);
    this.platos = [];
  }
}

// ============================================================================
// Encuentro entre dos chibis
// ============================================================================
class Encuentro {
  constructor(dir, a, b, def, guion) {
    Object.assign(this, { dir, a, b, def, guion });
    this.fase = 'acercarse'; this.t = 0; this.k = -1; this.tLinea = 0;
    a.encuentro = b.encuentro = this;
    dir.encuentros.add(this);
  }

  get conDormida() { return this.def.despierta && this.b.dormida; }

  empezar() {
    const { a, b, def } = this;
    a.cambiarAccion(def.id === 'regano' ? 'intervenir' : def.id === 'ofrecer_comida' ? 'repartir' : 'interactuar');
    if (def.caos) a.caosHasta = this.dir.tiempo + def.caos;
    if (!this.conDormida) { b.soltar(); b.estado = 'encuentro'; b.pose = 'quieta'; b.accion = { id: 'interactuar', prioridad: 5 }; }
    if (a.pos.distanceTo(b.pos) < 1.3) return this.llegar();
    a.irA(this.dir.mundo.celdaJunto(b.pos.x, b.pos.z, a.celda), () => this.llegar());
    if (a.estado !== 'caminando') this.cancelar();
  }

  llegar() {
    const { a, b } = this;
    this.fase = 'dialogo'; this.tLinea = 0.15;
    a.estado = 'encuentro'; a.pose = 'charlar'; a.mirarA(b.pos);
    if (!this.conDormida) { b.pose = 'charlar'; b.mirarA(a.pos); }
  }

  actualizar(dt) {
    this.t += dt;
    if (this.fase === 'acercarse') {
      if (!this.conDormida) this.b.mirarA(this.a.pos);
      if (this.t > 15) this.cancelar();
      return;
    }
    if ((this.tLinea -= dt) <= 0) this.siguiente();
  }

  siguiente() {
    const linea = this.guion.lineas[++this.k];
    if (!linea) return this.terminar();
    const [quien, texto, pose, emote] = linea;
    const h = quien ? this.b : this.a;
    if (pose && !(h === this.b && this.conDormida)) h.pose = pose;
    if (texto) this.dir.mundo.decir(h, texto, 2.6);
    if (emote) this.dir.mundo.emote(h, emote);
    this.tLinea = 2.1 + (texto?.length ?? 0) * 0.025;
  }

  terminar() {
    const { a, b, def, guion } = this;
    const quien = [a, b];
    for (const i of [0, 1]) if (guion.efectos?.[i]) quien[i].sumar(guion.efectos[i]);
    const dormida = this.conDormida;
    this.liberar();
    // la comida pasa a las manos de quien la recibe
    if (def.id === 'ofrecer_comida' && a.plato) {
      const p = a.plato; a.soltarPlato(false);
      if (guion.despues?.[1] === 'comerAqui') b.tomarPlato(p);
    }
    for (const i of [0, 1]) {
      const h = quien[i], sig = guion.despues?.[i];
      if (sig) h.ejecutar(sig, { objetivo: quien[1 - i] });
      else if (!(h === b && dormida)) h.terminar(azar(0.6, 1.6));
    }
  }

  liberar() {
    this.a.encuentro = this.b.encuentro = null;
    this.dir.encuentros.delete(this);
  }

  cancelar() {
    const dormida = this.conDormida;
    this.liberar();
    this.a.terminar(0.5);
    if (!dormida) this.b.terminar(0.5);
  }
}

// ============================================================================
// Habitante
// ============================================================================
export class Habitante {
  constructor(chibi, obj, mundo) {
    Object.assign(this, { chibi, obj, mundo });
    this.p = PERFILES[chibi.codigo];
    this.n = { ...this.p.inicial };
    this.t = Math.random() * 10;
    this.pose = 'quieta'; this.alto = 0;
    this.estado = 'libre'; this.espera = azar(0.5, 2);
    this.camino = []; this.alLlegar = null; this.uso = null; this.cfg = null;
    this.accion = null; this.encuentro = null; this.vistas = []; this.plato = null;
    this.caosHasta = 0; this.enfriaRegla = 0; this.utilidades = [];
    this.giroMeta = obj.raiz.rotation.y;
  }

  get codigo() { return this.chibi.codigo; }
  get dir() { return this.mundo.director; }
  get pos() { return this.obj.raiz.position; }
  get celda() { return this.mundo.aCelda(this.pos.x, this.pos.z); }
  get prioridad() { return this.encuentro ? 5 : (this.accion?.prioridad ?? 0); }
  get dormida() { return this.accion?.id === 'dormir' && this.estado === 'usando'; }
  get caos() {
    const a = this.accion;
    return this.caosHasta > this.dir.tiempo
      || (a?.id === 'travesura' && a.subida && this.estado === 'usando')
      || (a?.id === 'entrenar' && a.vueltas && !this.dir.diurno);
  }
  // quiénes están cerca (sin importar hacia dónde mira; para multitudes)
  cerca(r) { return this.mundo.habitantes.filter(o => o !== this && !o.dormida && o.pos.distanceTo(this.pos) <= r && o.estado !== 'editando'); }

  sumar(cambios) { for (const [k, v] of Object.entries(cambios)) if (k in this.n) this.n[k] = lim(this.n[k] + v); }

  acepta(a) {
    if (this.dormida) return false;
    const multitud = this.cerca(2.5).length >= 2 ? 0.4 : 0;
    const p = 0.35 + 0.5 * afinidad(this.codigo, a.codigo) + 0.4 * inv(this.n.social)
      - this.p.rasgos.introversion * 0.5 * (this.n.estres / 100 + multitud);
    return Math.random() < lim(p, 0.05, 0.98);
  }

  // --- ciclo de vida -----------------------------------------------------------
  colocarEn(i, j) {
    const p = this.mundo.aMundo(i, j);
    this.soltar(); this.soltarPlato();
    this.encuentro = null;
    this.pos.set(p.x, 0, p.z);
    this.obj.raiz.rotation.set(0, Math.random() * Math.PI * 2, 0);
    this.giroMeta = this.obj.raiz.rotation.y;
    this.terminar(azar(0.3, 1.5));
  }

  // deja el mueble que usaba (se levanta) y olvida el camino
  soltar() {
    if (this.uso) {
      const salida = this.estado === 'usando' && this.mundo.celdaJunto(this.uso.x, this.uso.z, this.celda);
      this.uso.ocupada = null; this.uso = null;
      if (salida) { const p = this.mundo.aMundo(...salida); this.pos.set(p.x, 0, p.z); }
    }
    this.camino = []; this.alLlegar = null; this.cfg = null;
    this.obj.raiz.rotation.x = 0; this.alto = 0;
  }

  terminar(espera = azar(0.8, 2.2)) {
    this.soltar();
    this.accion = null; this.estado = 'libre'; this.pose = 'quieta'; this.espera = espera;
  }

  cambiarAccion(id, extra = {}) {
    this.soltar();
    this.estado = 'libre';
    this.accion = { id, prioridad: extra.prioridad ?? PRIORIDAD[id] ?? 2, ...extra };
  }

  interrumpir(regla) {
    if (regla.efecto) this.sumar(regla.efecto);
    if (regla.emote) this.mundo.emote(this, regla.emote);
    const texto = regla.texto?.(this);
    if (texto) this.mundo.decir(this, texto, 2.4);
    this.ejecutar(regla.hacer, { prioridad: regla.prioridad });
  }

  tocar() {
    if (this.dormida) { this.mundo.decir(this, '¿Eh…? Cinco minutitos más…', 2.5); this.mundo.emote(this, '💤'); return; }
    if (this.encuentro || this.estado === 'editando') return;
    this.cambiarAccion('reaccion');
    this.quedarse({ pose: Math.random() < 0.5 ? 'saludar' : 'feliz', dur: 2.4 });
    this.mirarA(this.mundo.camara.position);
    this.mundo.decir(this, elegir(this.chibi.frases), 2.6);
  }

  // --- Utility AI ----------------------------------------------------------------
  // Cada acción recibe un puntaje con curvas sobre las necesidades; luego se multiplica por
  // el peso de la personalidad y por el horario. Gana el más alto (con un poco de ruido).
  evaluar() {
    const d = this.dir, n = this.n, P = this.p.pesos, m = this.mundo;
    const libres = act => m.usos.filter(u => u.act === act && m.usoLibre(u));
    const ops = [];
    const sumarOp = (id, base, extra = {}) => {
      const peso = P[id] ?? 1;
      if (base <= 0 || !peso) return;
      const hora = (HORARIO[d.fase]?.[id] ?? 1) * (this.p.horario[d.fase]?.[id] ?? 1);
      ops.push({ id, puntaje: base * peso * hora + (Math.random() - 0.5) * 0.05, ...extra });
    };

    const desvelo = this.p.horaDormir && d.hora >= 12 && d.hora < this.p.horaDormir && n.energia > 12 ? 0.15 : 1;
    sumarOp('dormir', (cuad(inv(n.energia)) * 1.2 + (d.fase === 'madrugada' ? 0.5 : d.hora >= 22 ? 0.35 : 0)) * desvelo);
    sumarOp('descansar', inv(n.energia) * 0.55 + n.estres / 100 * 0.35);
    sumarOp('comer', cuad(n.hambre / 100) * 1.3 + (d.platos.length ? 0.12 : 0));
    const ake = m.habitantes.find(h => h.codigo === 'hishiakebono' && h !== this);
    if (ake && !ake.encuentro && !ake.dormida && !['cocinar', 'repartir'].includes(ake.accion?.id))
      sumarOp('pedirComida', cuad(n.hambre / 100) * 1.4);
    if (libres('cocinar').length && !this.plato) {
      const otras = m.habitantes.filter(o => o !== this && !o.dormida);
      sumarOp('cocinar', (otras.length ? Math.max(...otras.map(necesitaCuidado)) : 0) * 0.9 + 0.08);
    }
    sumarOp('entrenar', inv(n.enfoque) * 0.9 * (n.energia > 30 ? 1 : 0.2));
    sumarOp('patrullar', inv(n.enfoque) * 0.6 + 0.12);
    if (libres('tele').length) sumarOp('tele', inv(n.diversion) * 0.7);
    sumarOp('pasear', 0.2 + inv(n.diversion) * 0.2);
    sumarOp('soledad', n.estres / 100 * 0.9 + (this.cerca(2.5).length >= 2 ? 0.3 : 0));
    sumarOp('travesura', inv(n.diversion) * 0.9 + 0.1);

    // el mejor encuentro posible con quien percibe (o con todas, si la interacción lo permite)
    let mejor = null;
    for (const def of INTERACCIONES) {
      if (def.cadena || !def.utilidad || (def.de !== '*' && def.de !== this.codigo)) continue;
      const candidatas = def.alcance === 'todas' ? m.habitantes.filter(o => o !== this) : this.vistas;
      for (const b of candidatas) {
        if ((def.a !== '*' && def.a !== b.codigo) || b.encuentro || b.estado === 'editando' || d.enfriado(def, this, b)) continue;
        if (b.dormida && !def.despierta && def.id !== 'broma') continue;
        const u = def.utilidad(this, b, d);
        if (u > 0 && (!mejor || u > mejor.u)) mejor = { u, def, b };
      }
    }
    if (mejor) sumarOp('interactuar', mejor.u, { def: mejor.def, objetivo: mejor.b });

    ops.sort((x, y) => y.puntaje - x.puntaje);
    this.utilidades = ops.slice(0, 4);
    return ops;
  }

  decidir() {
    const [op] = this.evaluar();
    if (!op) return this.ejecutar('pasear');
    this.ejecutar(op.id, op);
  }

  // --- ejecución de acciones ------------------------------------------------------
  ejecutar(id, op = {}) {
    const m = this.mundo, d = this.dir;
    const libres = act => m.usos.filter(u => u.act === act && m.usoLibre(u))
      .sort((x, y) => Math.hypot(x.x - this.pos.x, x.z - this.pos.z) - Math.hypot(y.x - this.pos.x, y.z - this.pos.z));
    this.cambiarAccion(id, { prioridad: op.prioridad });

    switch (id) {
      case 'dormir': {
        const fin = () => this.n.energia >= 98 && d.diurno;
        const cama = libres('dormir')[0];
        if (cama) return this.usar(cama, { actividad: 'dormir', pose: 'dormir', fin, dur: 400, frase: 'Zzz…' });
        // sin cama libre: cabecea sentada en el piso
        return this.irA(m.celdaJunto(this.pos.x, this.pos.z), () =>
          this.quedarse({ actividad: 'dormitar', pose: 'dormitar', fin, dur: 300, emote: '💤' }));
      }
      case 'levantarse': return this.terminar(0.4);
      case 'descansar': {
        const asiento = libres('sentarse')[0];
        if (asiento) return this.usar(asiento, { actividad: 'descansar', pose: 'sentarse', dur: azar(8, 14) });
        return this.quedarse({ actividad: 'descansar', pose: 'piso', dur: azar(6, 10) });
      }
      case 'comer': {
        const conPlato = new Set(d.platos.map(p => p.uid));
        const lugar = libres('comer').sort((x, y) => conPlato.has(y.uid) - conPlato.has(x.uid))[0];
        if (!lugar) return this.terminar();
        return this.usar(lugar, { actividad: 'comer', pose: 'comer', dur: 12, fin: () => this.n.hambre < 8,
          alAcomodarse: () => { if (d.tomarPlato(lugar.uid)) { this.sumar({ hambre: -40 }); this.mundo.emote(this, '✨'); } } });
      }
      case 'comerAqui':
        return this.quedarse({ actividad: 'comer', pose: 'comer', dur: 4.5, alTerminar: () => this.soltarPlato() });
      case 'pedirComida': {
        const ake = m.habitantes.find(h => h.codigo === 'hishiakebono');
        if (ake && !ake.encuentro && !ake.dormida && d.iniciarEncuentro(this, ake, interaccion('pedir_comida'))) return;
        return this.ejecutar('comer', { prioridad: op.prioridad });
      }
      case 'esperarComida':
        this.mundo.emote(this, '🍙');
        return this.quedarse({ actividad: 'descansar', pose: 'piso', dur: 30, fin: () => this.n.hambre < 40,
          alTerminar: () => { if (this.n.hambre >= 40) this.ejecutar('comer'); } });
      case 'cocinar': {
        const cocina = libres('cocinar')[0];
        if (!cocina || this.plato) return this.terminar();
        return this.usar(cocina, { actividad: 'cocinar', pose: 'cocinar', dur: azar(4, 6), emote: '♪',
          alTerminar: () => this.servir(op.objetivo) });
      }
      case 'entrenar': {
        const cinta = libres('correr')[0];
        if (cinta && Math.random() < 0.55) return this.usar(cinta, { actividad: 'entrenar', pose: 'correr', dur: azar(8, 13) });
        this.accion.vueltas = true;
        return this.darVueltas();
      }
      case 'patrullar': return this.patrullar(3);
      case 'tele': {
        const sitio = libres('tele')[0];
        if (!sitio) return this.terminar();
        return this.usar(sitio, { actividad: 'tele', pose: Math.random() < 0.6 ? 'piso' : 'quieta', dur: azar(8, 14) });
      }
      case 'pasear': {
        // Oguri gravita hacia Akebono; Stay Gold hacia Suzuka
        const iman = { oguricap: 'hishiakebono', staygold: 'silencesuzuka' }[this.codigo];
        const otra = iman && Math.random() < 0.5 && m.habitantes.find(h => h.codigo === iman);
        const destino = otra ? m.celdaJunto(otra.pos.x, otra.pos.z, this.celda) : m.celdaLibre();
        return this.irA(destino, () => this.quedarse({ actividad: 'pasear', pose: 'quieta', dur: azar(1, 3) }));
      }
      case 'soledad': {
        const destino = this.celdaLejos(m.habitantes.filter(o => o !== this).map(o => o.pos));
        return this.irA(destino, () => {
          this.giroMeta = Math.PI;   // mira por la ventana
          this.quedarse({ actividad: 'soledad', pose: 'quieta', dur: azar(7, 11) });
        });
      }
      case 'travesura': {
        const mesa = libres('subirse')[0];
        if (mesa && Math.random() < 0.45) {
          this.accion.subida = true;
          return this.usar(mesa, { actividad: 'travesura', pose: 'feliz', dur: azar(6, 10), frase: '¡Reina de la mesa! ♪' });
        }
        const def = interaccion('broma');
        const objetivos = (this.vistas.length ? this.vistas : m.habitantes.filter(o => o !== this))
          .filter(b => !b.encuentro && !d.enfriado(def, this, b))
          .map(b => ({ b, u: def.utilidad(this, b, d) })).sort((x, y) => y.u - x.u);
        if (objetivos[0] && d.iniciarEncuentro(this, objetivos[0].b, def)) return;
        return this.ejecutar('pasear');
      }
      case 'interactuar':
        if (!d.iniciarEncuentro(this, op.objetivo, op.def)) this.terminar(0.5);
        return;
      case 'intervenir': {
        const def = interaccion('regano');
        const culpable = this.vistas.find(o => o.caos && !o.encuentro && !d.enfriado(def, this, o));
        if (!culpable || !d.iniciarEncuentro(this, culpable, def)) this.terminar(0.5);
        return;
      }
      case 'toqueQueda': {
        const despierta = this.vistas.find(o => despiertaParaToque(this, o, d));
        if (!despierta || !d.iniciarEncuentro(this, despierta, interaccion('toque_queda'))) this.terminar(0.5);
        return;
      }
      case 'huir': {
        const feno = m.habitantes.find(h => h.codigo === 'fenomeno');
        this.mundo.emote(this, '♪');
        return this.irA(this.celdaLejos(feno ? [feno.pos] : []), () => this.terminar(), 'correr');
      }
      case 'llegar':
        this.mirarA(m.camara.position);
        return this.quedarse({ pose: 'feliz', dur: 3 });
      default:
        return this.terminar();
    }
  }

  // Akebono termina de cocinar: busca a quien más lo necesita (empieza por quien tiene a la vista)
  servir(objetivo) {
    this.plato = crearPlato();
    this.plato.position.set(0, 0.55, 0.3);
    this.obj.raiz.add(this.plato);
    const def = interaccion('ofrecer_comida');
    const candidatas = this.mundo.habitantes.filter(o => o !== this && !o.dormida && !o.encuentro && o.estado !== 'editando');
    let quien = objetivo && candidatas.includes(objetivo) ? objetivo : null;
    if (!quien) {
      const orden = candidatas.filter(o => !this.dir.enfriado(def, this, o))
        .map(o => ({ o, u: necesitaCuidado(o) + (this.vistas.includes(o) ? 0.15 : 0) }))
        .filter(x => x.u > 0.5).sort((x, y) => y.u - x.u);
      quien = orden[0]?.o;
    }
    if (quien && this.dir.iniciarEncuentro(this, quien, def)) return;
    // nadie lo necesita: lo deja en la mesa (Oguri lo huele desde lejos)
    const p = this.plato; this.plato = null;
    if (this.dir.dejarPlato(p)) this.mundo.decir(this, '¡Dejo comida en la mesa!', 2.2);
    this.terminar();
  }

  tomarPlato(p) { this.plato = p; p.position.set(0, 0.55, 0.3); this.obj.raiz.add(p); }
  soltarPlato() { if (this.plato) { this.plato.parent?.remove(this.plato); this.plato = null; } }

  // --- movimiento -------------------------------------------------------------------
  irA(celda, alLlegar, modo = 'caminar') {
    const camino = celda && ruta(this.mundo, this.celda, celda);
    if (!camino) { this.terminar(0.5); return; }
    this.camino = camino.slice(1).map(([i, j]) => this.mundo.aMundo(i, j));
    this.alLlegar = alLlegar; this.estado = 'caminando'; this.pose = modo; this.modo = modo;
  }

  usar(uso, cfg) {
    if (!uso) return this.terminar(0.5);
    uso.ocupada = this; this.uso = uso; this.cfg = cfg;
    const accion = this.accion;
    this.irA(this.mundo.celdaJunto(uso.x, uso.z, this.celda), () => {
      this.accion = accion;
      this.estado = 'acomodando'; this.desde = this.pos.clone(); this.prog = 0;
    });
    if (this.estado !== 'caminando') { uso.ocupada = null; this.uso = null; }
  }

  // se queda donde está haciendo algo (sin mueble)
  quedarse(cfg) {
    this.cfg = cfg; this.estado = 'usando'; this.pose = cfg.pose; this.espera = cfg.dur;
    if (cfg.emote) this.mundo.emote(this, cfg.emote);
  }

  celdaLejos(puntos) {
    let mejor = null, md = -1;
    for (const [i, j] of this.mundo.celdasLibres()) {
      const p = this.mundo.aMundo(i, j);
      const d = puntos.length ? Math.min(...puntos.map(q => Math.hypot(q.x - p.x, q.z - p.z))) : Math.random();
      if (d > md) { md = d; mejor = [i, j]; }
    }
    return mejor;
  }

  // Suzuka da vueltas al cuarto en sentido antihorario (como en la serie)
  darVueltas() {
    const { ancho, fondo } = this.mundo;
    const esquinas = [[1, fondo - 2], [ancho - 2, fondo - 2], [ancho - 2, 1], [1, 1]]
      .map(([i, j]) => { const p = this.mundo.aMundo(i, j); return this.mundo.celdaJunto(p.x, p.z) || [i, j]; });
    const vueltas = this.codigo === 'silencesuzuka' ? 2 : 1;
    const puntos = Array.from({ length: vueltas }, () => esquinas).flat();
    const siguiente = () => {
      const c = puntos.shift();
      if (!c) { this.mundo.decir(this, elegir(['¡Fiu!', 'Una vuelta más…', '…Qué bien se siente.']), 2); return this.terminar(); }
      this.irA(c, siguiente, 'correr');
    };
    siguiente();
  }

  patrullar(paradas) {
    const siguiente = () => {
      if (paradas-- <= 0) { if (Math.random() < 0.4) this.mundo.decir(this, 'Todo en orden.', 2); return this.terminar(); }
      this.irA(this.mundo.celdaLibre(), () => {
        this.quedarse({ actividad: 'patrullar', pose: 'quieta', dur: 1.2, sigue: true, alTerminar: siguiente });
      });
    };
    siguiente();
  }

  mirarA(p) { this.giroMeta = Math.atan2(p.x - this.pos.x, p.z - this.pos.z); }

  // --- cuadro a cuadro -----------------------------------------------------------------
  actividadActual() {
    if (this.estado === 'caminando') return this.modo;
    if (this.estado === 'encuentro') return this.encuentro?.fase === 'dialogo' ? 'charlar' : null;
    if (this.estado === 'usando' || this.estado === 'acomodando') return this.cfg?.actividad ?? null;
    return null;
  }

  actualizarNecesidades(dt) {
    const efecto = EFECTOS[this.actividadActual()] || {};
    for (const k of Object.keys(this.n)) {
      this.n[k] = lim(this.n[k] + ((DERIVA[k] ?? 0) * (this.p.ritmos[k] ?? 1) + (efecto[k] ?? 0)) * dt);
    }
    // a una introvertida le estresa estar rodeada
    if (this.p.rasgos.introversion > 0.6 && this.cerca(2).length >= 2) this.n.estres = lim(this.n.estres + 1.6 * dt);
  }

  actualizar(dt) {
    this.t += dt * (this.pose === 'correr' ? 11 : this.pose === 'caminar' ? 7 : this.pose === 'sorpresa' ? 4 : 2.2);
    if (this.estado === 'editando') return;
    this.actualizarNecesidades(dt);
    const raiz = this.obj.raiz;

    switch (this.estado) {
      case 'libre':
        if ((this.espera -= dt) <= 0) this.decidir();
        break;
      case 'caminando': {
        const meta = this.camino[0];
        if (!meta) {
          const f = this.alLlegar; this.alLlegar = null; this.pose = 'quieta';
          if (f) f(); else this.terminar();
          break;
        }
        const dx = meta.x - this.pos.x, dz = meta.z - this.pos.z, d = Math.hypot(dx, dz);
        const paso = VEL[this.modo] * dt;
        if (d <= paso) { this.pos.x = meta.x; this.pos.z = meta.z; this.camino.shift(); }
        else { this.pos.x += dx / d * paso; this.pos.z += dz / d * paso; this.giroMeta = Math.atan2(dx, dz); }
        break;
      }
      case 'acomodando': {
        this.prog = Math.min(1, this.prog + dt * 2.2);
        const u = this.uso;
        if (!u) { this.terminar(); break; }
        this.pos.lerpVectors(this.desde, new THREE.Vector3(u.x, 0, u.z), this.prog);
        this.giroMeta = u.rot;
        if (this.prog >= 1) {
          const c = this.cfg;
          this.estado = 'usando'; this.alto = u.alto ?? 0; this.pose = c.pose; this.espera = c.dur;
          c.alAcomodarse?.();
          if (c.frase) this.mundo.decir(this, c.frase, 2.4);
          if (c.emote) this.mundo.emote(this, c.emote);
        }
        break;
      }
      case 'usando': {
        if (this.encuentro) break;   // alguien le habla: espera a que termine
        this.espera -= dt;
        const c = this.cfg;
        if (this.espera <= 0 || c?.fin?.()) {
          const despues = c?.alTerminar;
          if (c?.sigue) { this.cfg = null; despues(); }   // sigue con la misma acción (p. ej. otra parada de la patrulla)
          else { this.terminar(); despues?.(); }
        }
        break;
      }
    }

    // giro suave
    let dif = this.giroMeta - raiz.rotation.y;
    dif = Math.atan2(Math.sin(dif), Math.cos(dif));
    raiz.rotation.y += dif * Math.min(1, dt * 9);

    const durmiendo = this.pose === 'dormir';
    raiz.rotation.x = durmiendo ? -Math.PI / 2 : 0;
    const y = this.obj.esqueleto.posar(this.pose, this.t, { alto: this.alto });
    raiz.position.y = durmiendo ? this.alto + 0.12
      : ['sentarse', 'piso', 'dormitar'].includes(this.pose) ? y
      : this.alto + Math.max(0, y);
    this.obj.sombra.position.set(this.pos.x, 0.015, this.pos.z);
    this.obj.sombra.visible = !durmiendo && !this.alto;
  }
}
