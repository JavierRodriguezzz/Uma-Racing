// Animaciones con anime.js (cargado globalmente desde cdnjs). Si no está disponible o el usuario
// pidió reducir el movimiento, todo se muestra al instante.
const reducir = matchMedia("(prefers-reduced-motion: reduce)").matches;

export function listo() {
  return new Promise((r) => (window.anime ? r() : addEventListener("load", r, { once: true })));
}

const puede = () => window.anime && !reducir && !document.hidden;

/** Entrada escalonada de los hijos de un contenedor (tarjetas, filas, premios...). */
export function entrada(objetivos, { desde = 18, retraso = 55 } = {}) {
  if (!puede()) return;
  window.anime({
    targets: objetivos,
    opacity: [0, 1],
    translateY: [desde, 0],
    duration: 520,
    delay: window.anime.stagger(retraso),
    easing: "easeOutCubic",
  });
}

/** Cuenta desde el valor actual del elemento hasta `valor` (marcador tipo arcade). */
export function contar(el, valor, { formato = (n) => n.toLocaleString("es-MX"), duracion = 900 } = {}) {
  if (!el) return;
  const actual = Number(el.dataset.valor ?? (String(el.textContent).replace(/[^\d-]/g, "") || 0));
  el.dataset.valor = valor;
  if (!puede() || actual === valor) { el.textContent = formato(valor); return; }
  const obj = { n: actual };
  window.anime({
    targets: obj, n: valor, round: 1, duration: duracion, easing: "easeOutExpo",
    update: () => { el.textContent = formato(obj.n); },
  });
  window.anime({ targets: el, scale: [1.25, 1], duration: 500, easing: "easeOutElastic(1, .5)" });
}

/** Sacudida corta (error, apuesta perdida). */
export function sacudir(el) {
  if (!puede() || !el) return;
  window.anime({ targets: el, translateX: [0, -10, 9, -6, 4, 0], duration: 420, easing: "easeInOutSine" });
}

/** Estallido de píxeles de colores desde un elemento (victoria, premio épico). */
export function estallido(el, colores = ["#ff3ea5", "#38e8ff", "#ffd23f", "#5dffb0"], cantidad = 28) {
  if (!puede() || !el) return;
  const r = el.getBoundingClientRect();
  const capa = document.createElement("div");
  capa.style.cssText = `position:fixed;left:${r.left + r.width / 2}px;top:${r.top + r.height / 2}px;pointer-events:none;z-index:220`;
  for (let i = 0; i < cantidad; i++) {
    const p = document.createElement("i");
    p.style.cssText = `position:absolute;width:8px;height:8px;background:${colores[i % colores.length]};box-shadow:0 0 8px ${colores[i % colores.length]}`;
    capa.appendChild(p);
  }
  document.body.appendChild(capa);
  window.anime({
    targets: capa.children,
    translateX: () => window.anime.random(-180, 180),
    translateY: () => window.anime.random(-160, 120),
    scale: [{ value: 1.4, duration: 200 }, { value: 0, duration: 700 }],
    rotate: () => window.anime.random(-180, 180),
    easing: "easeOutCubic",
    duration: 900,
    complete: () => capa.remove(),
  });
}
