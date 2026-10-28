// Carga de chibis y animación por huesos.
// Los modelos vienen en pose T y sin animaciones, así que las poses (caminar, correr, sentarse,
// dormir, saludar, comer…) se generan girando los huesos alrededor de los ejes del personaje.
import * as THREE from 'three';
import { FBXLoader } from 'three/addons/loaders/FBXLoader.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { rampa } from './muebles.js';

export const ALTURA = 1.25;   // estatura de una chibi en celdas
const RUTA = '/modelos/chibis';
const texturas = new THREE.TextureLoader();

// Nombre de material → parte del cuerpo (las texturas de cada chibi están en datos.js)
function parte(nombre) {
  const n = nombre.toLowerCase();
  if (n.includes('hair')) return 'pelo';
  if (n.includes('tail')) return 'cola';
  if (n.includes('brow') || n.includes('mayu')) return 'cejas';
  if (n.includes('cheek')) return 'mejillas';
  if (n.includes('eye')) return 'ojos';
  if (n.includes('mouth')) return 'boca';
  if (n.includes('face') || n.includes('head')) return 'cara';
  if (n.includes('body') || n.includes('bdy')) return 'cuerpo';
  return null;
}
const SOBREPUESTAS = new Set(['ojos', 'boca', 'cejas']);   // usan recorte por alfa

function vestir(raiz, chibi, esGLB) {
  raiz.traverse(o => {
    if (!o.isMesh) return;
    const lista = [].concat(o.material).map(m => {
      const p = parte(m.name || o.name);
      const archivo = chibi.texturas[p];
      let map = esGLB && m.map && !archivo ? m.map : null;
      if (archivo) {
        map = texturas.load(`${RUTA}/${chibi.codigo}/${archivo}.png`);
        map.flipY = !esGLB;
      }
      if (map) map.colorSpace = THREE.SRGBColorSpace;
      return new THREE.MeshToonMaterial({
        name: m.name, map, gradientMap: rampa, side: THREE.DoubleSide,
        transparent: p === 'mejillas', depthWrite: p !== 'mejillas',
        alphaTest: SOBREPUESTAS.has(p) ? 0.5 : 0,
      });
    });
    o.material = Array.isArray(o.material) ? lista : lista[0];
    o.frustumCulled = false;
  });
}

const buscar = (raiz, re) => { let b = null; raiz.traverse(o => { if (!b && o.isBone && re.test(o.name)) b = o; }); return b; };

export async function cargarChibi(chibi) {
  const url = `${RUTA}/${chibi.codigo}/${chibi.modelo}`;
  const esGLB = chibi.modelo.endsWith('.glb');
  const modelo = esGLB ? (await new GLTFLoader().loadAsync(url)).scene : await new FBXLoader().loadAsync(url);
  vestir(modelo, chibi, esGLB);

  // ajuste: escala a ALTURA y pies en el origen
  const ajuste = new THREE.Group(); ajuste.add(modelo);
  const raiz = new THREE.Group(); raiz.add(ajuste);
  raiz.rotation.order = 'YXZ';   // primero el giro (Y) y luego acostarse (X) sobre su propio costado
  raiz.updateMatrixWorld(true);
  let caja = new THREE.Box3().setFromObject(modelo, true);
  ajuste.scale.setScalar(ALTURA / caja.getSize(new THREE.Vector3()).y);
  raiz.updateMatrixWorld(true);
  caja = new THREE.Box3().setFromObject(modelo, true);
  const centro = caja.getCenter(new THREE.Vector3());
  ajuste.position.set(-centro.x, -caja.min.y, -centro.z);
  raiz.updateMatrixWorld(true);

  // sombra redonda (más barata que sombras reales en mallas con huesos)
  const sombra = new THREE.Mesh(new THREE.CircleGeometry(0.28, 24),
    new THREE.MeshBasicMaterial({ color: '#08061a', transparent: true, opacity: 0.35, depthWrite: false }));
  sombra.rotation.x = -Math.PI / 2; sombra.position.y = 0.015;

  // cápsula invisible para hacer clic
  const golpe = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.3, ALTURA, 8), new THREE.MeshBasicMaterial({ visible: false }));
  golpe.position.y = ALTURA / 2; raiz.add(golpe);

  return { raiz, ajuste, sombra, golpe, esqueleto: new Esqueleto(modelo, raiz) };
}

// ----------------------------------------------------------------------------
// Esqueleto con poses procedurales
// ----------------------------------------------------------------------------
const EJE_X = new THREE.Vector3(1, 0, 0), EJE_Y = new THREE.Vector3(0, 1, 0), EJE_Z = new THREE.Vector3(0, 0, 1);
const _q = new THREE.Quaternion(), _q2 = new THREE.Quaternion(), _v = new THREE.Vector3(), _v2 = new THREE.Vector3();

class Esqueleto {
  constructor(modelo, raiz) {
    this.raiz = raiz;
    const h = re => buscar(modelo, re);
    this.b = {
      cadera: h(/(^|_)Hip$/i), cintura: h(/(^|_)(Waist|Spine)$/i), cuello: h(/(^|_)Neck$/i), cabeza: h(/(^|_)Head$/i),
      muslo: [h(/Thigh_L$/i), h(/Thigh_R$/i)], rodilla: [h(/Knee_L$/i), h(/Knee_R$/i)],
      brazo: [h(/(^|_)Arm_L$/i), h(/(^|_)Arm_R$/i)], codo: [h(/(Elbow|Forearm)_L$/i), h(/(Elbow|Forearm)_R$/i)],
      cola: h(/Tail/i),
    };
    this.lado = [1, -1];
    // de pose T a brazos abajo: apunta cada brazo hacia su codo pegado al cuerpo
    raiz.updateMatrixWorld(true);
    this.b.brazo.forEach((brazo, i) => {
      const codo = this.b.codo[i];
      if (!brazo || !codo) return;
      const a = brazo.getWorldPosition(new THREE.Vector3()), b = codo.getWorldPosition(new THREE.Vector3());
      const dir = b.sub(a).normalize();
      this.lado[i] = Math.sign(dir.x) || this.lado[i];
      const meta = new THREE.Vector3(this.lado[i] * 0.32, -1, 0.06).normalize();
      this.girarMundo(brazo, _q2.setFromUnitVectors(dir, meta));
      raiz.updateMatrixWorld(true);
    });
    this.reposo = new Map();
    for (const v of Object.values(this.b)) for (const hueso of [].concat(v)) if (hueso) this.reposo.set(hueso, hueso.quaternion.clone());
    // altura de la cadera (para sentarse a la altura correcta)
    const m = this.b.muslo[0];
    this.pierna = m ? raiz.worldToLocal(m.getWorldPosition(new THREE.Vector3())).y : ALTURA * 0.35;
  }

  // aplica una rotación expresada en el espacio del mundo
  girarMundo(hueso, qMundo) {
    hueso.parent.getWorldQuaternion(_q);
    const inv = _q.clone().invert();
    hueso.quaternion.premultiply(inv.multiply(qMundo).multiply(_q));
  }
  // gira un hueso alrededor de un eje del personaje (X = costado, Y = arriba, Z = frente)
  girar(hueso, eje, ang) {
    if (!hueso || !ang) return;
    hueso.parent.updateWorldMatrix(true, false);
    this.raiz.getWorldQuaternion(_q2);
    _v.copy(eje).applyQuaternion(_q2);
    this.girarMundo(hueso, new THREE.Quaternion().setFromAxisAngle(_v, ang));
  }

  // pose = { nombre, t } → coloca huesos y devuelve el desplazamiento vertical del cuerpo
  posar(nombre, t, extra = {}) {
    for (const [hueso, q] of this.reposo) hueso.quaternion.copy(q);
    const { muslo, rodilla, brazo, codo, cabeza, cadera, cola } = this.b;
    const s = Math.sin(t), resp = Math.sin(t * 0.35);
    let y = 0;
    const brazos = (a0, a1) => { this.girar(brazo[0], EJE_X, a0); this.girar(brazo[1], EJE_X, a1); };
    const codos = a => { this.girar(codo[0], EJE_X, a); this.girar(codo[1], EJE_X, a); };
    const costado = (i, a) => this.girar(brazo[i], EJE_Z, a * this.lado[i]);   // + = levanta hacia afuera

    switch (nombre) {
      case 'caminar': case 'correr': {
        const k = nombre === 'correr' ? 1.6 : 1;
        this.girar(muslo[0], EJE_X, -0.45 * k * s); this.girar(muslo[1], EJE_X, 0.45 * k * s);
        this.girar(rodilla[0], EJE_X, Math.max(0, s) * 0.7 * k); this.girar(rodilla[1], EJE_X, Math.max(0, -s) * 0.7 * k);
        brazos(0.5 * k * s, -0.5 * k * s);
        if (k > 1) { codos(-0.9); this.girar(cadera, EJE_X, -0.18); }
        y = Math.abs(Math.cos(t)) * 0.025 * k;
        break;
      }
      case 'sentarse': case 'piso': case 'dormitar': {
        for (const i of [0, 1]) { this.girar(muslo[i], EJE_X, -1.5); this.girar(rodilla[i], EJE_X, nombre === 'sentarse' ? 1.5 : 0.4); }
        brazos(-0.35, -0.35); codos(-0.5);
        if (nombre === 'dormitar') this.girar(cabeza, EJE_X, 0.38 + 0.04 * resp);   // cabeceando
        else this.girar(cabeza, EJE_Z, resp * 0.08);
        y = (extra.alto ?? 0) - this.pierna + 0.04;
        break;
      }
      case 'cocinar':   // revuelve la olla con las dos manos
        brazos(-0.95 + 0.18 * Math.sin(t * 3), -0.95 - 0.18 * Math.sin(t * 3)); codos(-0.9);
        this.girar(cabeza, EJE_X, 0.18);
        break;
      case 'ofrecer':   // extiende el plato con ambas manos
        brazos(-1.3, -1.3); codos(-0.25);
        this.girar(cabeza, EJE_Z, 0.12 * Math.sin(t * 0.8));
        break;
      case 'senalar':   // una mano en la cintura, la otra apunta
        this.girar(brazo[1], EJE_X, -1.5); this.girar(codo[1], EJE_X, -0.1 * Math.max(0, Math.sin(t * 2.5)));
        costado(0, 0.55); this.girar(codo[0], EJE_X, -1.4);
        this.girar(cabeza, EJE_X, -0.08 * Math.abs(Math.sin(t * 1.5)));
        break;
      case 'cruzada':   // brazos cruzados y la cara volteada: "nop"
        brazos(-0.75, -0.75); codos(-1.9);
        this.girar(brazo[0], EJE_Y, -0.45 * this.lado[0]); this.girar(brazo[1], EJE_Y, -0.45 * this.lado[1]);
        this.girar(cabeza, EJE_Y, 0.5); this.girar(cabeza, EJE_X, -0.12);
        break;
      case 'sorpresa':
        costado(0, 1.5); costado(1, 1.5); codos(-0.4);
        y = Math.max(0, Math.sin(t * 4)) * 0.16;
        break;
      case 'cansada':
        brazos(0.12, 0.12);
        this.girar(cadera, EJE_X, 0.12); this.girar(cabeza, EJE_X, 0.32);
        y = -0.01 + 0.008 * resp;
        break;
      case 'dormir':
        brazos(0, 0); costado(0, 0.15); costado(1, 0.15);
        this.girar(cabeza, EJE_Y, 0.35);
        break;
      case 'saludar':
        costado(1, 2.4); this.girar(codo[1], EJE_Z, this.lado[1] * (0.4 + 0.35 * Math.sin(t * 2.2)));
        this.girar(cabeza, EJE_Z, 0.12);
        break;
      case 'comer':
        brazos(-0.3, -1.25 - 0.25 * Math.max(0, Math.sin(t * 1.6))); this.girar(codo[1], EJE_X, -1.3);
        this.girar(cabeza, EJE_X, 0.1 * Math.max(0, Math.sin(t * 1.6)));
        break;
      case 'feliz':
        costado(0, 2.2 + 0.2 * s); costado(1, 2.2 + 0.2 * s);
        y = Math.abs(Math.sin(t * 1.2)) * 0.22;
        break;
      case 'charlar':
        brazos(-0.2 + 0.15 * Math.sin(t * 1.3), -0.1); this.girar(codo[0], EJE_X, -0.6);
        this.girar(cabeza, EJE_Z, 0.08 * Math.sin(t * 0.9));
        break;
      default: // quieta: respira y mira alrededor
        brazos(0.05 * resp, 0.05 * resp);
        this.girar(cabeza, EJE_Y, 0.25 * Math.sin(t * 0.21));
        y = 0.006 * resp;
    }
    if (cola) this.girar(cola, EJE_Y, Math.sin(t * (nombre === 'feliz' ? 3 : 0.9)) * 0.35);
    return y;
  }
}
