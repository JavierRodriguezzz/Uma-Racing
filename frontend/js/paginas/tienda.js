import { get, patch, post } from "../api.js";
import { actualizarMonedas, iniciarPagina } from "../layout.js";
import { $, $$, cargando, celebrarLogros, confirmar, debounce, error, esc, modal, num, paginacion, tipoItem, toast, vacio } from "../ui.js";

const usuario = await iniciarPagina();
const lista = $("#lista");
const estado = { page: 1, limit: 8 };
const CANDADO = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/></svg>';

let equipado = null;

function filtros() {
  const f = Object.fromEntries(new FormData($("#filtros")));
  // los chibis y muebles se compran dentro del dormitorio
  return { ...f, seccion: "juego", page: estado.page, limit: estado.limit };
}

async function cargar() {
  cargando(lista, 5);
  try {
    const [res, inv] = await Promise.all([get("/items", filtros()), get("/perfil/inventario")]);
    equipado = inv.datos.find((i) => i.equipado)?.id;
    pintar(res);
  } catch (e) {
    error(lista, e, cargar);
    $("#paginacion").innerHTML = "";
  }
}

function tarjeta(i) {
  const bloqueado = !i.poseido;
  const accion = bloqueado
    ? `<button class="btn btn-oro btn-sm" data-comprar="${i.id}" ${usuario.monedas < i.precio ? 'title="Saldo insuficiente"' : ""}>Comprar</button>`
    : i.tipo === "escenario"
      ? (i.id === equipado ? '<span class="badge exito">Equipado</span>' : `<button class="btn btn-sm" data-equipar="${i.id}">Equipar</button>`)
      : '<span class="badge exito">Desbloqueado</span>';
  return `<article class="tarjeta item ${i.tipo}">
    <button class="portada" data-detalle="${i.id}" style="border:0;padding:0;cursor:pointer" aria-label="Ver detalle de ${esc(i.nombre)}">
      <img src="/${esc(i.imagen_url || "img/logo.png")}" alt="" loading="lazy">
      ${bloqueado ? `<div class="candado">${CANDADO}</div>` : ""}
    </button>
    <div class="cuerpo">
      <div class="fila" style="justify-content:space-between"><h3 style="margin:0">${esc(i.nombre)}</h3><span class="badge info">${tipoItem(i.tipo)}</span></div>
      <p class="texto-2" style="margin:0;font-size:14px">${esc(i.descripcion)}</p>
      <div class="pie"><span class="precio">${i.es_gratuito ? "Gratis" : `${num(i.precio)} 🪙`}</span>${accion}</div>
    </div>
  </article>`;
}

function pintar(res) {
  if (!res.datos.length) {
    vacio(lista, "Sin resultados", "Ningún artículo coincide con la búsqueda. Prueba con otros filtros.", "🔍");
  } else {
    lista.innerHTML = `<div class="grid grid-items">${res.datos.map(tarjeta).join("")}</div>`;
    const porId = Object.fromEntries(res.datos.map((i) => [i.id, i]));
    $$("[data-comprar]", lista).forEach((b) => b.addEventListener("click", () => comprar(porId[b.dataset.comprar], b)));
    $$("[data-equipar]", lista).forEach((b) => b.addEventListener("click", () => equipar(porId[b.dataset.equipar])));
    $$("[data-detalle]", lista).forEach((b) => b.addEventListener("click", () => detalle(b.dataset.detalle)));
  }
  paginacion($("#paginacion"), res, (p) => { estado.page = p; cargar(); });
}

async function comprar(item, boton) {
  if (usuario.monedas < item.precio) {
    toast(`Saldo insuficiente: te faltan ${num(item.precio - usuario.monedas)} monedas. Mira anuncios para ganar más.`, "aviso");
    return;
  }
  const ok = await confirmar(`¿Comprar ${item.nombre} por ${num(item.precio)} monedas? Te quedarán ${num(usuario.monedas - item.precio)}.`,
    { titulo: "Confirmar compra", texto: "Comprar" });
  if (!ok) return;
  boton.disabled = true;
  try {
    const r = await post("/compras", { item_id: item.id });
    usuario.monedas = r.saldo;
    actualizarMonedas(r.saldo);
    toast(`¡${item.nombre} desbloqueado! Folio ${r.folio}`, "exito");
    celebrarLogros(r.logros_nuevos);
    cargar();
  } catch (e) {
    toast(e.message, "error");
    boton.disabled = false;
  }
}

async function equipar(item) {
  try {
    await patch("/perfil/escenario", { item_id: item.id });
    toast(`Escenario "${item.nombre}" equipado para tus próximas carreras.`, "exito");
    cargar();
  } catch (e) {
    toast(e.message, "error");
  }
}

async function detalle(id) {
  try {
    const i = await get(`/items/${id}`);
    modal({
      titulo: i.nombre,
      contenido: `<div class="grid" style="grid-template-columns:minmax(0,160px) 1fr;align-items:start">
        <img src="/${esc(i.imagen_url || "img/logo.png")}" alt="" style="border-radius:10px;background:var(--cielo)">
        <div><p>${esc(i.descripcion)}</p>
          <p><strong>Tipo:</strong> ${tipoItem(i.tipo)}<br>
          <strong>Precio:</strong> ${i.es_gratuito ? "Gratis" : `${num(i.precio)} monedas`}<br>
          <strong>Estado:</strong> ${i.poseido ? "En tu inventario" : "Bloqueado"}<br>
          <strong>Jugadores que lo compraron:</strong> ${num(i.ventas)}</p>
          ${i.tipo === "personaje" ? '<p class="texto-2" style="font-size:13px">En el juego, el Jugador 2 (invitado) también puede usar los personajes que tengas.</p>' : ""}
        </div></div>`,
    });
  } catch (e) {
    toast(e.message, "error");
  }
}

const recargar = () => { estado.page = 1; cargar(); };
$("#q").addEventListener("input", debounce(recargar));
$$("#filtros select").forEach((s) => s.addEventListener("change", recargar));
$("#filtros").addEventListener("submit", (e) => { e.preventDefault(); recargar(); });
cargar();
