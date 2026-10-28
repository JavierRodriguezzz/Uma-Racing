// Muebles y habitación hechos con figuras de three.js (sin modelos externos).
// Convención: 1 celda = 1 unidad; cada mueble tiene su origen en el centro de su huella,
// a nivel del piso, y su frente mira hacia +Z. Para cambiar uno por un modelo real basta con
// que el constructor devuelva el modelo cargado con ese mismo origen y orientación.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

// Rampa de 3 tonos para el sombreado tipo anime
const rampa = (() => {
  const t = new THREE.DataTexture(new Uint8Array([90, 90, 90, 255, 185, 185, 185, 255, 255, 255, 255, 255]), 3, 1);
  t.minFilter = t.magFilter = THREE.NearestFilter; t.needsUpdate = true;
  return t;
})();
export const toon = (color, extra = {}) => new THREE.MeshToonMaterial({ color, gradientMap: rampa, ...extra });
export { rampa };

const c = (hex, l = 0) => new THREE.Color(hex).offsetHSL(0, 0, l);

function caja(g, w, h, d, color, x = 0, y = 0, z = 0, r = 0.04) {
  const m = new THREE.Mesh(new RoundedBoxGeometry(w, h, d, 2, Math.min(r, w / 2, h / 2, d / 2)), toon(color));
  m.position.set(x, y + h / 2, z); m.castShadow = m.receiveShadow = true;
  g.add(m); return m;
}
function cilindro(g, rt, rb, h, color, x = 0, y = 0, z = 0, seg = 20) {
  const m = new THREE.Mesh(new THREE.CylinderGeometry(rt, rb, h, seg), toon(color));
  m.position.set(x, y + h / 2, z); m.castShadow = m.receiveShadow = true;
  g.add(m); return m;
}
const brillo = (color, intensidad = 1.4) =>
  new THREE.MeshBasicMaterial({ color: c(color).multiplyScalar(intensidad) });

const CONSTRUCTORES = {
  sofa(g, col) {
    caja(g, 1.9, 0.22, 0.85, c(col, -0.25), 0, 0.06, 0.02);         // base
    caja(g, 0.9, 0.16, 0.7, col, -0.47, 0.28, 0.08);                 // cojines
    caja(g, 0.9, 0.16, 0.7, col, 0.47, 0.28, 0.08);
    caja(g, 1.9, 0.55, 0.2, c(col, -0.12), 0, 0.28, -0.34);          // respaldo
    caja(g, 0.16, 0.42, 0.85, c(col, -0.12), -0.9, 0.06, 0.02);      // brazos
    caja(g, 0.16, 0.42, 0.85, c(col, -0.12), 0.9, 0.06, 0.02);
    for (const x of [-0.85, 0.85]) for (const z of [-0.33, 0.37]) cilindro(g, 0.04, 0.04, 0.06, '#211b4f', x, 0, z, 8);
  },
  cama(g, col) {
    caja(g, 1.9, 0.3, 2.85, '#2a2350', 0, 0, 0);                     // armazón
    caja(g, 1.8, 0.16, 2.7, '#f1edff', 0, 0.3, 0.02);                // colchón
    caja(g, 1.84, 0.1, 1.75, col, 0, 0.42, 0.5);                     // cobija
    caja(g, 1.1, 0.12, 0.45, '#ffffff', 0, 0.46, -1.0, 0.06);        // almohada
    caja(g, 1.9, 0.9, 0.14, c(col, -0.2), 0, 0, -1.38);              // cabecera
    const tira = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.04, 0.02), brillo(col));
    tira.position.set(0, 0.75, -1.3); g.add(tira);
  },
  mesa(g, col) {
    caja(g, 1.7, 0.08, 1.4, col, 0, 0.32, 0);
    for (const x of [-0.72, 0.72]) for (const z of [-0.55, 0.55]) caja(g, 0.1, 0.32, 0.1, c(col, -0.3), x, 0, z, 0.02);
    // platillos: Oguri siempre los encuentra
    cilindro(g, 0.18, 0.15, 0.04, '#ffffff', -0.35, 0.4, 0.1);
    cilindro(g, 0.11, 0.11, 0.08, '#ff9a3d', -0.35, 0.44, 0.1, 12);
    cilindro(g, 0.07, 0.06, 0.14, '#38e8ff', 0.4, 0.4, -0.2, 12);
  },
  refri(g, col) {
    caja(g, 0.8, 1.6, 0.75, col, 0, 0, 0);
    caja(g, 0.76, 0.02, 0.02, c(col, -0.3), 0, 1.05, 0.38);
    caja(g, 0.04, 0.3, 0.04, '#9aa4c7', 0.3, 1.2, 0.39);
    caja(g, 0.04, 0.3, 0.04, '#9aa4c7', 0.3, 0.6, 0.39);
  },
  tele(g, col) {
    caja(g, 1.9, 0.4, 0.7, '#f1edff', 0, 0, -0.05);                  // mueble
    caja(g, 1.8, 0.02, 0.02, '#ffd23f', 0, 0.3, 0.31);
    caja(g, 0.2, 0.12, 0.2, '#211b4f', 0, 0.4, -0.1);                // pie
    caja(g, 1.7, 0.95, 0.08, col, 0, 0.52, -0.1, 0.03);              // marco
    const pantalla = new THREE.Mesh(new THREE.PlaneGeometry(1.56, 0.82), new THREE.MeshBasicMaterial({ color: '#38e8ff' }));
    pantalla.position.set(0, 1.0, -0.055); pantalla.name = 'pantalla'; g.add(pantalla);
  },
  arcade(g, col) {
    caja(g, 0.8, 1.7, 0.7, '#17133a', 0, 0, -0.02);
    caja(g, 0.82, 0.3, 0.72, col, 0, 1.5, -0.02);                    // marquesina
    const pantalla = new THREE.Mesh(new THREE.PlaneGeometry(0.62, 0.48), new THREE.MeshBasicMaterial({ color: '#ff3ea5' }));
    pantalla.position.set(0, 1.12, 0.34); pantalla.rotation.x = -0.25; pantalla.name = 'pantalla'; g.add(pantalla);
    caja(g, 0.8, 0.1, 0.35, '#211b4f', 0, 0.82, 0.2);                // tablero
    cilindro(g, 0.03, 0.03, 0.08, '#ffd23f', -0.15, 0.92, 0.22, 8);
    cilindro(g, 0.035, 0.035, 0.03, '#38e8ff', 0.1, 0.92, 0.25, 10);
    cilindro(g, 0.035, 0.035, 0.03, '#ff5c7a', 0.22, 0.92, 0.2, 10);
  },
  caminadora(g, col) {
    caja(g, 0.75, 0.14, 1.8, '#211b4f', 0, 0, 0.05);
    caja(g, 0.6, 0.03, 1.6, '#08061a', 0, 0.14, 0.05, 0.01);         // banda
    caja(g, 0.06, 1.05, 0.06, col, -0.33, 0, -0.8, 0.02);
    caja(g, 0.06, 1.05, 0.06, col, 0.33, 0, -0.8, 0.02);
    caja(g, 0.72, 0.16, 0.22, col, 0, 1.0, -0.78);                   // tablero
  },
  puf(g, col) {
    const m = cilindro(g, 0.36, 0.4, 0.34, col, 0, 0, 0, 24);
    m.scale.set(1, 1, 1);
    cilindro(g, 0.3, 0.36, 0.04, c(col, 0.12), 0, 0.33, 0, 24);
  },
  planta(g) {
    cilindro(g, 0.24, 0.18, 0.36, '#f1edff', 0, 0, 0, 16);
    cilindro(g, 0.03, 0.03, 0.3, '#6b4a2a', 0, 0.34, 0, 6);
    const hojas = new THREE.Mesh(new THREE.IcosahedronGeometry(0.38, 1), toon('#5dc77a', { flatShading: true }));
    hojas.position.y = 0.92; hojas.castShadow = true; g.add(hojas);
  },
  lampara(g, col) {
    cilindro(g, 0.18, 0.2, 0.05, '#211b4f', 0, 0, 0, 16);
    cilindro(g, 0.025, 0.025, 1.3, '#9aa4c7', 0, 0.05, 0, 6);
    const pantalla = new THREE.Mesh(new THREE.CylinderGeometry(0.18, 0.26, 0.3, 18, 1, true), brillo(col, 1));
    pantalla.position.y = 1.45; pantalla.material.side = THREE.DoubleSide; g.add(pantalla);
    const luz = new THREE.PointLight(col, 1.2, 3.5, 1.5); luz.position.y = 1.35; g.add(luz);
  },
  estante(g, col) {
    caja(g, 1.8, 1.5, 0.5, col, 0, 0, -0.2);
    for (const y of [0.45, 0.95]) caja(g, 1.7, 0.04, 0.45, c(col, 0.15), 0, y, -0.17, 0.01);
    // trofeos
    for (const [x, y, t] of [[-0.55, 0.49, '#ffd23f'], [0, 0.49, '#c9cbd6'], [0.5, 0.99, '#ffd23f'], [-0.3, 0.99, '#b07a4a']]) {
      cilindro(g, 0.07, 0.1, 0.06, '#211b4f', x, y, -0.15, 10);
      cilindro(g, 0.1, 0.04, 0.2, t, x, y + 0.06, -0.15, 12);
    }
  },
  alfombra(g, col, variante) {
    const forma = variante.id === 'alfombra_pista'
      ? new THREE.Mesh(new THREE.RingGeometry(0.75, 1.45, 48), toon(col, { side: THREE.DoubleSide }))
      : new THREE.Mesh(new THREE.CircleGeometry(1.45, 48), toon(col));
    forma.rotation.x = -Math.PI / 2; forma.position.y = 0.012; forma.receiveShadow = true; g.add(forma);
    const centro = new THREE.Mesh(new THREE.RingGeometry(0.55, 0.7, 40, 1, 0.6, Math.PI * 1.6), toon(c(col, -0.25)));
    centro.rotation.x = -Math.PI / 2; centro.position.y = 0.016; g.add(centro);   // herradura
  },
};

// Crea el mueble de una variante. Devuelve un Group con userData de su tipo.
export function crearMueble(tipo, def, variante) {
  const g = new THREE.Group();
  (CONSTRUCTORES[tipo] || ((gr, col) => caja(gr, def.tam[0] * 0.9, 0.8, def.tam[1] * 0.9, col)))(g, variante.color, variante);
  g.userData = { tipo, id: variante.id };
  return g;
}

// ----------------------------------------------------------------------------
// Habitación: piso de baldosas, dos muros con ventana a la ciudad nocturna y rejilla de edición
// ----------------------------------------------------------------------------
export function crearCuarto({ ancho, fondo }) {
  const g = new THREE.Group();
  const piso = new THREE.Mesh(new THREE.PlaneGeometry(ancho, fondo), toon('#2b2560'));
  piso.rotation.x = -Math.PI / 2; piso.receiveShadow = true; piso.name = 'piso'; g.add(piso);

  // baldosas en tablero (dos tonos muy cercanos)
  const bal = new THREE.InstancedMesh(new THREE.PlaneGeometry(0.98, 0.98), toon('#332c6e'), ancho * fondo);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion().setFromEuler(new THREE.Euler(-Math.PI / 2, 0, 0));
  let n = 0;
  for (let i = 0; i < ancho; i++) for (let j = 0; j < fondo; j++) {
    if ((i + j) % 2) continue;
    m.compose(new THREE.Vector3(i - ancho / 2 + 0.5, 0.002, j - fondo / 2 + 0.5), q, new THREE.Vector3(1, 1, 1));
    bal.setMatrixAt(n++, m);
  }
  bal.count = n; bal.receiveShadow = true; g.add(bal);

  const alto = 3.2, grosor = 0.25;
  const muro = (w, color) => { const mm = new THREE.Mesh(new THREE.BoxGeometry(w, alto, grosor), toon(color)); mm.receiveShadow = true; return mm; };
  const fondoM = muro(ancho + grosor, '#e9e4ff'); fondoM.position.set(0, alto / 2, -fondo / 2 - grosor / 2); g.add(fondoM);
  const izq = muro(fondo, '#d9d2ff'); izq.rotation.y = Math.PI / 2; izq.position.set(-ancho / 2 - grosor / 2, alto / 2, 0); g.add(izq);

  // zoclo y franja neón
  for (const [w, x, z, ry] of [[ancho, 0, -fondo / 2 + 0.02, 0], [fondo, -ancho / 2 + 0.02, 0, Math.PI / 2]]) {
    const z1 = new THREE.Mesh(new THREE.BoxGeometry(w, 0.16, 0.04), toon('#4a3fa3')); z1.position.set(x, 0.08, z); z1.rotation.y = ry; g.add(z1);
    const f = new THREE.Mesh(new THREE.BoxGeometry(w, 0.05, 0.03), brillo('#ff3ea5', 1)); f.position.set(x, 2.55, z); f.rotation.y = ry; g.add(f);
  }

  // ventana con ciudad nocturna (textura dibujada en canvas)
  const ventana = new THREE.Mesh(new THREE.PlaneGeometry(4.2, 1.9), new THREE.MeshBasicMaterial({ map: ciudad() }));
  ventana.position.set(2.6, 1.55, -fondo / 2 + 0.04); g.add(ventana);
  const marco = new THREE.Mesh(new THREE.BoxGeometry(4.4, 2.1, 0.05), toon('#4a3fa3'));
  marco.position.set(2.6, 1.55, -fondo / 2 + 0.01); g.add(marco);
  for (const x of [1.2, 2.6, 4.0]) { const p = new THREE.Mesh(new THREE.BoxGeometry(0.06, 1.9, 0.04), toon('#4a3fa3')); p.position.set(x, 1.55, -fondo / 2 + 0.06); g.add(p); }

  // cartel neón "UMA" en el muro izquierdo
  const cartel = new THREE.Mesh(new THREE.PlaneGeometry(2.2, 0.8), new THREE.MeshBasicMaterial({ map: textoNeon('UMA ♥ DORM'), transparent: true }));
  cartel.rotation.y = Math.PI / 2; cartel.position.set(-ancho / 2 + 0.02, 1.9, -0.5); g.add(cartel);
  return g;
}

export function crearRejilla({ ancho, fondo }) {
  const pts = [];
  for (let i = 0; i <= ancho; i++) pts.push(i - ancho / 2, 0.02, -fondo / 2, i - ancho / 2, 0.02, fondo / 2);
  for (let j = 0; j <= fondo; j++) pts.push(-ancho / 2, 0.02, j - fondo / 2, ancho / 2, 0.02, j - fondo / 2);
  const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  const r = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: '#38e8ff', transparent: true, opacity: 0.35 }));
  r.visible = false; return r;
}

function ciudad() {
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 232;
  const x = cv.getContext('2d');
  const grad = x.createLinearGradient(0, 0, 0, cv.height);
  grad.addColorStop(0, '#08061a'); grad.addColorStop(1, '#3a1650');
  x.fillStyle = grad; x.fillRect(0, 0, cv.width, cv.height);
  for (let i = 0; i < 60; i++) { x.fillStyle = 'rgba(255,255,255,.7)'; x.fillRect(Math.random() * 512, Math.random() * 90, 1.5, 1.5); }
  x.fillStyle = '#ffd23f'; x.beginPath(); x.arc(420, 50, 18, 0, Math.PI * 2); x.fill();
  let px = 0;
  while (px < 512) {
    const w = 24 + Math.random() * 46, h = 60 + Math.random() * 120;
    x.fillStyle = '#120e30'; x.fillRect(px, cv.height - h, w, h);
    for (let wy = cv.height - h + 8; wy < cv.height - 6; wy += 12)
      for (let wx = px + 5; wx < px + w - 6; wx += 9)
        if (Math.random() < 0.35) { x.fillStyle = Math.random() < 0.5 ? '#38e8ff' : '#ff3ea5'; x.fillRect(wx, wy, 4, 5); }
    px += w + 3;
  }
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}

function textoNeon(txt) {
  const cv = document.createElement('canvas'); cv.width = 512; cv.height = 186;
  const x = cv.getContext('2d');
  x.font = '700 76px Bungee, "Chakra Petch", sans-serif'; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.shadowColor = '#ff3ea5'; x.shadowBlur = 24; x.fillStyle = '#ffd6ec';
  x.fillText(txt, 256, 96); x.fillText(txt, 256, 96);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; return t;
}
