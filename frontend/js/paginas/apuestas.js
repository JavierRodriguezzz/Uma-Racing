import { del, get, post } from "../api.js";
import { entrada, estallido, listo, sacudir } from "../fx.js";
import { actualizarMonedas, iniciarPagina } from "../layout.js";
import { tablaPaginada } from "../tabla.js";
import { $, $$, cargando, confirmar, debounce, error, esc, fechaHora, num, toast } from "../ui.js";

const usuario = await iniciarPagina();
await listo();
const COLOR = { goldship: "#ff5c7a", oguricap: "#38e8ff", elcondorpasa: "#ffd23f", junglepocket: "#5dffb0" };
let info = null;
let elegida = null;
let corriendo = false;

function responsable(l) {
  $("#responsable").innerHTML = `🎲 <strong>Juego responsable:</strong> apuestas de ${l.minimo} a ${l.maximo} monedas virtuales.
    Te quedan <strong>${num(l.disponible_hoy)}</strong> de ${num(l.perdida_max_dia)} monedas de pérdida permitida hoy. Las monedas no tienen valor monetario.`;
}

// ---------------------------------------------------------------- Pestañas
$$("[data-tab]").forEach((b) => b.addEventListener("click", () => {
  $$("[data-tab]").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
  $$("[data-panel]").forEach((p) => (p.hidden = p.dataset.panel !== b.dataset.tab));
  if (b.dataset.tab === "tiempo") cargarReto();
  if (b.dataset.tab === "historial") hist.recargar();
  entrada($$(`[data-panel="${b.dataset.tab}"] > *`));
}));

// ---------------------------------------------------------------- Carrera simulada
const barra = (etq, v) => `<div class="atributo"><span>${etq}</span><div class="progreso magenta"><div style="width:${v}%"></div></div></div>`;

async function cargarCarrera() {
  cargando($("#corredoras"), 3);
  try {
    info = await get("/apuestas/carrera");
    responsable(info.limites);
    $("#corredoras").innerHTML = info.corredoras.map((c) => `
      <button class="corredora" data-id="${c.id}" aria-pressed="false" style="--color:${COLOR[c.codigo]}">
        <img src="/${esc(c.imagen_url)}" alt="">
        <strong>${esc(c.nombre)}</strong>
        <div class="momio">×${c.momio.toFixed(2)}</div>
        <div class="texto-3" style="font-size:12px;margin-bottom:6px">${(c.probabilidad * 100).toFixed(1)} % de ganar</div>
        ${barra("VELOCIDAD", c.velocidad)}${barra("RESISTENCIA", c.resistencia)}${barra("ARRANQUE", c.arranque)}
      </button>`).join("");
    entrada($$("#corredoras > *"), { retraso: 80 });
    $$(".corredora").forEach((b) => b.addEventListener("click", () => elegir(Number(b.dataset.id))));
    pintarPista();
  } catch (e) { error($("#corredoras"), e, cargarCarrera); }
}

function elegir(id) {
  if (corriendo) return;
  elegida = info.corredoras.find((c) => c.id === id);
  $$(".corredora").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.id) === id)));
  $("#apostar").disabled = false;
  pagoPosible();
  pintarPista();
}

function pagoPosible() {
  const m = Number($("#monto").value) || 0;
  $("#pago-posible").textContent = elegida ? `${num(Math.floor(m * elegida.momio))} 🪙` : "—";
}

$("#fichas").innerHTML = [10, 50, 100, 250, 500].map((v) => `<button type="button" class="btn btn-sm" data-ficha="${v}">${v}</button>`).join("");
$$("[data-ficha]").forEach((b) => b.addEventListener("click", () => { $("#monto").value = b.dataset.ficha; pagoPosible(); }));
$("#monto").addEventListener("input", pagoPosible);

function pintarPista() {
  $("#pista").innerHTML = '<div class="meta-linea"></div>' + info.corredoras.map((c, i) => `
    <div class="carril ${elegida?.id === c.id ? "mia" : ""}" data-carril="${c.id}">
      <span class="num-carril">${i + 1}</span>
      <div class="corredor" style="--color:${COLOR[c.codigo]}"><img src="/${esc(c.imagen_url)}" alt="${esc(c.nombre)}"></div>
    </div>`).join("");
}

$("#apostar").addEventListener("click", async () => {
  if (!elegida || corriendo) return;
  const monto = Number($("#monto").value);
  if (!(monto >= info.limites.minimo && monto <= info.limites.maximo)) {
    sacudir($("#monto"));
    return toast(`La apuesta debe ser de ${info.limites.minimo} a ${info.limites.maximo} monedas.`, "aviso");
  }
  if (monto > usuario.monedas) { sacudir($("#monto")); return toast("No tienes monedas suficientes.", "aviso"); }
  corriendo = true;
  $("#apostar").disabled = true;
  try {
    const r = await post("/apuestas/carrera", { item_id: elegida.id, monto });
    usuario.monedas = r.saldo - r.pago;
    actualizarMonedas(usuario.monedas);
    $("#folio-carrera").textContent = r.folio;
    await animarCarrera(r);
    usuario.monedas = r.saldo;
    actualizarMonedas(r.saldo);
    info.limites = r.limites;
    responsable(r.limites);
  } catch (e) {
    toast(e.message, "error");
    sacudir($("#apostar"));
  } finally {
    corriendo = false;
    $("#apostar").disabled = false;
  }
});

/** Reproduce la carrera EXACTA que decidió el servidor (posiciones por turno). */
function animarCarrera(r) {
  pintarPista();
  const pista = $("#pista");
  const ancho = pista.clientWidth * 0.96 - 58;
  const cuadros = r.carrera.cuadros;
  const ms = 4800 / cuadros.length;
  $("#pista").scrollIntoView({ behavior: "smooth", block: "center" });
  const anims = info.corredoras.map((c, i) => new Promise((ok) => {
    const el = $(`[data-carril="${c.id}"] .corredor`, pista);
    if (!window.anime) { el.style.transform = `translateX(${(cuadros.at(-1)[i] / 1000) * ancho}px)`; return ok(); }
    window.anime({
      targets: el,
      translateX: cuadros.map((f) => ({ value: (f[i] / 1000) * ancho, duration: ms })),
      translateY: cuadros.map((_, k) => ({ value: k % 2 ? -3 : 0, duration: ms })),   // trote
      easing: "linear",
      complete: ok,
    });
  }));
  return Promise.all(anims).then(() => {
    const ganadora = info.corredoras.find((c) => c.id === r.ganadora);
    const cartel = document.createElement("div");
    cartel.className = `cartel-resultado ${r.gano ? "gano" : "perdio"}`;
    cartel.innerHTML = `<div><div class="pixel texto-2">GANÓ ${esc(ganadora.nombre.toUpperCase())}</div>
      <h2>${r.gano ? `¡+${num(r.pago)} MONEDAS!` : "SIN PREMIO"}</h2>
      <div class="texto-2">Apostaste ${num(r.monto)} a ${esc(elegida.nombre)} con momio ×${r.momio.toFixed(2)}</div></div>`;
    pista.appendChild(cartel);
    if (window.anime) window.anime({ targets: cartel.querySelector("h2"), scale: [0.3, 1], opacity: [0, 1], duration: 700, easing: "easeOutElastic(1, .6)" });
    if (r.gano) estallido(cartel.querySelector("h2"), undefined, 40); else sacudir(pista);
  });
}

// ---------------------------------------------------------------- Reto de tiempo
async function cargarReto(objetivo = 25) {
  const cont = $("#reto");
  cargando(cont, 4);
  try {
    const q = await get("/apuestas/tiempo/cotizar", { objetivo_s: objetivo });
    responsable(q.limites);
    if (q.pendiente) return pintarPendiente(q.pendiente);
    cont.innerHTML = `
      <div class="tarjeta-titulo"><h2>Gana tu próxima carrera en menos de…</h2></div>
      <p class="texto-2" style="margin-top:0">Apuesta a que, como Jugador 1, ganas tu próxima partida real por debajo del tiempo objetivo.
        El momio se calcula con tus últimas ${q.victorias_consideradas} victorias${q.mejor_tiempo_ms ? ` (tu mejor tiempo: ${(q.mejor_tiempo_ms / 1000).toFixed(2)} s)` : ""}.</p>
      <div class="grid grid-2" style="align-items:center">
        <div>
          <div class="titulo neon-cian" style="font-size:48px;line-height:1" id="obj-txt">${objetivo.toFixed(1)} s</div>
          <input type="range" id="objetivo" min="8" max="90" step="0.5" value="${objetivo}" aria-label="Tiempo objetivo en segundos">
          <div class="fila" style="justify-content:space-between;font-size:12px" class="texto-3"><span>8 s · difícil</span><span>90 s · fácil</span></div>
        </div>
        <div class="grid grid-kpi">
          <div class="tarjeta kpi oro"><span class="etiqueta">Momio</span><span class="valor" id="t-momio">×${q.momio.toFixed(2)}</span></div>
          <div class="tarjeta kpi cielo"><span class="etiqueta">Probabilidad</span><span class="valor" id="t-prob">${Math.round(q.probabilidad_estimada * 100)}%</span></div>
        </div>
      </div>
      <div class="fila" style="margin-top:16px;justify-content:space-between">
        <div class="campo" style="margin:0;max-width:220px"><label for="t-monto">Monto</label><input id="t-monto" type="number" min="10" max="500" step="10" value="50"></div>
        <div class="fila"><span class="texto-2">Pago si ganas: <strong class="neon-ficha" id="t-pago">${num(Math.floor(50 * q.momio))}</strong></span>
          <button class="btn btn-primario btn-grande" id="t-apostar">Aceptar reto</button></div>
      </div>`;
    let momio = q.momio;
    const recotizar = debounce(async (v) => {
      try {
        const n = await get("/apuestas/tiempo/cotizar", { objetivo_s: v });
        momio = n.momio;
        $("#t-momio").textContent = `×${n.momio.toFixed(2)}`;
        $("#t-prob").textContent = `${Math.round(n.probabilidad_estimada * 100)}%`;
        $("#t-pago").textContent = num(Math.floor(Number($("#t-monto").value) * momio));
      } catch { /* se mantiene la cotización anterior */ }
    }, 250);
    $("#objetivo").addEventListener("input", (e) => { $("#obj-txt").textContent = `${Number(e.target.value).toFixed(1)} s`; recotizar(e.target.value); });
    $("#t-monto").addEventListener("input", () => ($("#t-pago").textContent = num(Math.floor(Number($("#t-monto").value) * momio))));
    $("#t-apostar").addEventListener("click", async () => {
      const objetivo_s = Number($("#objetivo").value), monto = Number($("#t-monto").value);
      if (!(await confirmar(`¿Apostar ${num(monto)} monedas a que ganas tu próxima carrera en menos de ${objetivo_s} s?`, { texto: "Aceptar reto" }))) return;
      try {
        const r = await post("/apuestas/tiempo", { objetivo_s, monto });
        actualizarMonedas(r.saldo);
        usuario.monedas = r.saldo;
        toast(`Reto ${r.folio} aceptado. ¡Ve a jugar!`, "exito");
        cargarReto();
      } catch (e) { toast(e.message, "error"); sacudir($("#t-apostar")); }
    });
  } catch (e) { error(cont, e, () => cargarReto()); }
}

function pintarPendiente(p) {
  $("#reto").innerHTML = `
    <div class="tarjeta-titulo"><h2>Reto en curso</h2><span class="badge aviso">Pendiente</span></div>
    <p class="titulo neon-cian" style="font-size:32px;margin:0">&lt; ${(p.objetivo_ms / 1000).toFixed(1)} s</p>
    <p class="texto-2">Apostaste <strong>${num(p.monto)}</strong> monedas con momio <strong>×${Number(p.momio).toFixed(2)}</strong>
      (${esc(p.folio)}, ${fechaHora(p.creada_en)}). Se resuelve automáticamente en tu próxima partida como Jugador 1.</p>
    <div class="fila"><a class="btn btn-primario" href="/jugar.html">▶ Ir a jugar</a><button class="btn btn-peligro" id="cancelar-reto">Cancelar y recuperar monedas</button></div>`;
  $("#cancelar-reto").addEventListener("click", async () => {
    if (!(await confirmar("¿Cancelar el reto? Se devolverán tus monedas.", { texto: "Cancelar reto", peligro: true }))) return;
    try { const r = await del(`/apuestas/${encodeURIComponent(p.folio)}`); actualizarMonedas(r.saldo); toast(r.mensaje, "exito"); cargarReto(); }
    catch (e) { toast(e.message, "error"); }
  });
}

// ---------------------------------------------------------------- Historial
const ESTADO = { ganada: "exito", perdida: "peligro", pendiente: "aviso", cancelada: "" };
const hist = tablaPaginada({
  contenedor: $("#t-hist"), endpoint: "/apuestas", filtros: $("#f-hist"), ordenInicial: "-fecha", limite: 10,
  vacio: ["Sin apuestas", "Tus apuestas aparecerán aquí."],
  columnas: [
    { titulo: "Folio", render: (a) => `<code>${esc(a.folio)}</code>` },
    { titulo: "Fecha", orden: "fecha", render: (a) => fechaHora(a.creada_en) },
    { titulo: "Tipo", render: (a) => (a.tipo === "carrera" ? `🏁 ${esc(a.eleccion)}` : `⏱ &lt; ${(a.objetivo_ms / 1000).toFixed(1)} s`) },
    { titulo: "Monto", orden: "monto", clase: "num", render: (a) => num(a.monto) },
    { titulo: "Momio", orden: "momio", clase: "num", render: (a) => `×${a.momio.toFixed(2)}` },
    { titulo: "Pago", orden: "pago", clase: "num", render: (a) => (a.pago ? `<strong class="neon-ficha">+${num(a.pago)}</strong>` : "0") },
    { titulo: "Resultado", clase: "envolver", render: (a) => `<span class="badge ${ESTADO[a.estado]}">${esc(a.estado)}</span> <span class="texto-2" style="font-size:13px">${esc(a.resultado || "")}</span>` },
  ],
});

cargarCarrera();
if (location.hash === "#tiempo") $('[data-tab="tiempo"]').click();
