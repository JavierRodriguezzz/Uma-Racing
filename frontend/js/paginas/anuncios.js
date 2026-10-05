import { get, post } from "../api.js";
import { actualizarMonedas, iniciarPagina } from "../layout.js";
import { $, $$, cargando, celebrarLogros, error, esc, modal, num, toast, vacio } from "../ui.js";

await iniciarPagina();
const lista = $("#lista");
let restantes = 0;

async function cargar() {
  cargando(lista, 4);
  try {
    const res = await get("/anuncios", { limit: 50 });
    restantes = res.restantes_hoy;
    $("#limite").textContent = `${res.vistos_hoy} de ${res.limite_diario} vistos hoy`;
    $("#limite").className = `badge ${restantes ? "info" : "aviso"}`;
    if (!res.datos.length) return vacio(lista, "No hay anuncios disponibles", "Vuelve más tarde.", "📺");
    lista.innerHTML = `${restantes ? "" : '<div class="alerta advertencia">Ya viste todos los anuncios con recompensa de hoy. Vuelve mañana.</div>'}
      <div class="grid grid-2">${res.datos.map((a) => `
        <article class="tarjeta anuncio">
          <div class="muestra" style="background:${esc(a.color)}" aria-hidden="true">${esc(a.titulo[0])}</div>
          <div style="flex:1;min-width:0"><h3 style="margin:0">${esc(a.titulo)}</h3>
            <div class="texto-2" style="font-size:14px">${esc(a.anunciante)} · ${a.duracion_seg} s</div>
            <div class="precio" style="font-weight:800;color:var(--aviso)">+${num(a.recompensa_monedas)} monedas</div></div>
          <button class="btn btn-primario" data-ver="${a.id}" ${restantes ? "" : "disabled"}>▶ Ver</button>
        </article>`).join("")}</div>`;
    const porId = Object.fromEntries(res.datos.map((a) => [a.id, a]));
    $$("[data-ver]", lista).forEach((b) => b.addEventListener("click", () => ver(porId[b.dataset.ver], b)));
  } catch (e) {
    error(lista, e, cargar);
  }
}

async function ver(anuncio, boton) {
  boton.disabled = true;
  let v;
  try {
    v = await post(`/anuncios/${anuncio.id}/ver`);
  } catch (e) {
    toast(e.message, "error");
    boton.disabled = false;
    return;
  }
  const total = v.duracion_seg;
  const inicio = performance.now();
  const m = modal({
    titulo: "Anuncio",
    contenido: `<div class="reproductor" style="background:linear-gradient(135deg, ${esc(anuncio.color)}, #1e3b2a)">
        <div class="texto-3" style="color:#ffffffb0;font-size:12px;text-transform:uppercase;letter-spacing:.1em">Publicidad simulada · ${esc(anuncio.anunciante)}</div>
        <h2>${esc(anuncio.titulo)}</h2><p>${esc(anuncio.descripcion)}</p>
        <div class="contador" id="contador" aria-live="polite">${total}</div>
        <div class="barra"><div id="barra"></div></div>
      </div>
      <p class="texto-2" style="margin-top:12px" id="nota">Si cierras esta ventana antes de terminar, no recibirás la recompensa.</p>`,
    acciones: [{ texto: "Reclamar recompensa", clase: "btn-oro", alHacerClic: (cerrar, b) => reclamar(cerrar, b) }],
  });
  const btnReclamar = $("footer .btn", m.raiz);
  btnReclamar.disabled = true;

  const tick = setInterval(() => {
    if (!document.body.contains(m.raiz)) { clearInterval(tick); boton.disabled = false; return; }
    const pasados = (performance.now() - inicio) / 1000;
    const faltan = Math.max(0, Math.ceil(total - pasados));
    $("#contador", m.raiz).textContent = faltan ? faltan : "¡Listo!";
    $("#barra", m.raiz).style.width = `${Math.min(100, (pasados / total) * 100)}%`;
    if (!faltan) { clearInterval(tick); btnReclamar.disabled = false; $("#nota", m.raiz).textContent = "¡Gracias por ver el anuncio! Reclama tu recompensa."; }
  }, 200);

  async function reclamar(cerrar, b) {
    b.disabled = true;
    try {
      const r = await post(`/anuncios/visualizaciones/${v.token}/completar`);
      actualizarMonedas(r.saldo);
      toast(`+${r.monedas_otorgadas} monedas. Saldo: ${num(r.saldo)}`, "exito");
      celebrarLogros(r.logros_nuevos);
      cerrar();
      cargar();
    } catch (e) {
      toast(e.message, "error");
      b.disabled = false;
    }
  }
}

cargar();
