import { get, post } from "../api.js";
import { entrada, estallido, listo, sacudir } from "../fx.js";
import { actualizarMonedas, iniciarPagina } from "../layout.js";
import { tablaPaginada } from "../tabla.js";
import { $, $$, cargando, celebrarLogros, confirmar, error, esc, fechaHora, num, toast } from "../ui.js";

const usuario = await iniciarPagina();
await listo();
const RAREZA = { comun: "Común", rara: "Rara", epica: "Épica" };
const COLOR = { comun: "#9aa4c7", rara: "#38b6ff", epica: "#ff3ea5" };
const ORDEN = { comun: 0, rara: 1, epica: 2 };
let info = null;
let girando = false;

function icono(p) {
  if (p.imagen_url) return `<img src="/${esc(p.imagen_url)}" alt="">`;
  return `<span aria-hidden="true">${(p.monedas ?? 0) >= 150 ? "💰" : "🪙"}</span>`;
}

function medidor(n) {
  $("#pity-txt").textContent = `${n} / ${info.garantia}`;
  $("#medidor").innerHTML = Array.from({ length: info.garantia }, (_, i) => `<i class="${i < n ? "lleno" : ""}"></i>`).join("");
}

async function cargar() {
  cargando($("#probabilidades"), 4);
  try {
    info = await get("/gacha");
    $("#costo1").textContent = num(info.costo_1);
    $("#costo10").textContent = num(info.costo_10);
    medidor(info.sin_epica);
    $("#probabilidades").innerHTML = `
      <div class="fila" style="margin-bottom:12px">${Object.entries(info.rarezas).map(([r, p]) =>
        `<span class="badge r-${r}">${RAREZA[r]} ${(p * 100).toFixed(0)} %</span>`).join("")}</div>
      <div class="premios-grid">${info.premios.map((p) => `
        <div class="premio ${p.rareza}">
          <div class="rareza">${RAREZA[p.rareza]}</div>
          <div class="icono">${icono(p)}</div>
          <div class="nombre">${esc(p.nombre)}</div>
          <div class="texto-2 mono" style="font-size:12px">${(p.probabilidad * 100).toFixed(2)} %</div>
          <div class="texto-3" style="font-size:11px">${p.tipo === "monedas" ? `+${num(p.monedas)} monedas` : p.poseido ? `Ya lo tienes · repetido +${num(p.monedas_repetido)}` : "¡Nuevo para ti!"}</div>
        </div>`).join("")}</div>`;
    entrada($$("#probabilidades .premio"), { retraso: 40 });
  } catch (e) { error($("#probabilidades"), e, cargar); }
}

// ---------------------------------------------------------------- Animación de la máquina
function animarMaquina(rarezaMayor) {
  return new Promise((ok) => {
    if (!window.anime) return ok();
    $("#color-capsula").setAttribute("fill", COLOR[rarezaMayor]);
    const tl = window.anime.timeline({ complete: ok });
    tl.add({ targets: "#perilla", rotate: [0, 360], duration: 900, easing: "easeInOutBack" })
      .add({ targets: "#capsulas-domo", translateY: [0, -10, 4, -6, 0], translateX: [0, 6, -6, 3, 0], duration: 600, easing: "easeInOutSine" }, "-=700")
      .add({ targets: "#maquina", rotate: [0, -2, 2, -1, 0], duration: 420, easing: "easeInOutSine" }, "-=300")
      .add({ targets: "#capsula", opacity: [0, 1], translateX: [88, 88], translateY: [300, 352], duration: 520, easing: "easeOutBounce" })
      .add({ targets: "#capsula", scale: [1, 1.25], duration: 200, easing: "easeOutQuad" })
      .add({ targets: "#tapa", translateY: -26, rotate: -35, duration: 380, easing: "easeOutBack" })
      .add({ targets: "#capsula", opacity: 0, duration: 300, easing: "linear" });
  });
}

function reiniciarCapsula() {
  if (!window.anime) return;
  window.anime.set("#capsula", { opacity: 0, translateX: 88, translateY: 300, scale: 1 });
  window.anime.set("#tapa", { translateY: 0, rotate: 0 });
  window.anime.set("#perilla", { rotate: 0 });
}

function mostrar(r) {
  const cont = $("#revelado");
  cont.innerHTML = `<div class="${r.resultados.length > 1 ? "capsulas" : ""}" style="${r.resultados.length > 1 ? "" : "max-width:220px;margin:0 auto"}">
    ${r.resultados.map((x) => `
      <div class="premio ${x.rareza}">
        <div class="rareza">${RAREZA[x.rareza]}${x.por_garantia ? " · GARANTÍA" : ""}</div>
        <div class="icono">${icono(x)}</div>
        <div class="nombre">${esc(x.nombre)}</div>
        <div class="texto-2" style="font-size:12px">${x.repetido ? `Repetido → +${num(x.monedas)}` : x.monedas ? `+${num(x.monedas)} monedas` : "¡Desbloqueado!"}</div>
      </div>`).join("")}</div>`;
  cont.closest(".tarjeta").scrollIntoView({ behavior: "smooth", block: "nearest" });
  const cartas = $$(".premio", cont);
  if (window.anime) {
    window.anime({ targets: cartas, opacity: [0, 1], rotateY: [90, 0], scale: [0.6, 1], delay: window.anime.stagger(110), duration: 600, easing: "easeOutBack" });
  }
  setTimeout(() => cartas.forEach((c, i) => { if (r.resultados[i].rareza === "epica") estallido(c); }), 110 * r.resultados.length + 300);
}

async function tirar(cantidad) {
  if (girando) return;
  const costo = cantidad === 1 ? info.costo_1 : info.costo_10;
  if (usuario.monedas < costo) {
    sacudir($(cantidad === 1 ? "#tirar1" : "#tirar10"));
    return toast(`Necesitas ${num(costo)} monedas. Consigue más en "Comprar monedas" o viendo anuncios.`, "aviso");
  }
  if (cantidad === 10 && !(await confirmar(`¿Hacer 10 tiradas por ${num(costo)} monedas?`, { texto: "Tirar ×10" }))) return;
  girando = true;
  $$("#tirar1, #tirar10").forEach((b) => (b.disabled = true));
  reiniciarCapsula();
  try {
    const r = await post("/gacha/tiradas", { cantidad });
    const mayor = r.resultados.reduce((m, x) => (ORDEN[x.rareza] > ORDEN[m] ? x.rareza : m), "comun");
    actualizarMonedas(r.saldo - r.resultados.reduce((s, x) => s + x.monedas, 0));   // primero se cobra la tirada
    usuario.monedas = r.saldo;
    await animarMaquina(mayor);
    actualizarMonedas(r.saldo);                                                     // luego llegan los premios
    $("#folio").textContent = r.folio;
    mostrar(r);
    medidor(r.sin_epica);
    celebrarLogros(r.logros_nuevos);
    hist.recargar();
    if (r.resultados.some((x) => x.tipo === "item" && !x.repetido)) cargar();   // actualiza "ya lo tienes"
  } catch (e) {
    toast(e.message, "error");
  } finally {
    girando = false;
    $$("#tirar1, #tirar10").forEach((b) => (b.disabled = false));
  }
}

$("#tirar1").addEventListener("click", () => tirar(1));
$("#tirar10").addEventListener("click", () => tirar(10));

const hist = tablaPaginada({
  contenedor: $("#t-hist"), endpoint: "/gacha/tiradas", filtros: $("#f-hist"), ordenInicial: "-fecha", limite: 10,
  vacio: ["Sin tiradas", "Tus premios aparecerán aquí."],
  columnas: [
    { titulo: "Folio", render: (t) => `<code>${esc(t.folio)}</code>` },
    { titulo: "Fecha", orden: "fecha", render: (t) => fechaHora(t.creada_en) },
    { titulo: "Premio", render: (t) => esc(t.premio) },
    { titulo: "Rareza", orden: "rareza", render: (t) => `<span class="badge r-${t.rareza}">${RAREZA[t.rareza]}</span>${t.por_garantia ? ' <span class="badge info">Garantía</span>' : ""}` },
    { titulo: "Monedas", clase: "num", render: (t) => (t.monedas_otorgadas ? `+${num(t.monedas_otorgadas)}` : "—") },
    { titulo: "", render: (t) => (t.repetido ? '<span class="texto-3">repetido</span>' : "") },
  ],
});

cargar();
