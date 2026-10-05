// Utilidades de interfaz: escape de HTML, formatos, estados, toasts, modales, paginación y tablas.

// Todo dato que viene de la API se escapa antes de insertarlo en el DOM (evita XSS).
export function esc(valor) {
  return String(valor ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export const $ = (sel, raiz = document) => raiz.querySelector(sel);
export const $$ = (sel, raiz = document) => [...raiz.querySelectorAll(sel)];

// ---------------------------------------------------------------- Formatos
const fmtNum = new Intl.NumberFormat("es-MX");
export const num = (n) => fmtNum.format(Number(n || 0));
export const fecha = (v) => (v ? new Date(v).toLocaleDateString("es-MX", { day: "2-digit", month: "short", year: "numeric" }) : "—");
export const fechaHora = (v) => (v ? new Date(v).toLocaleString("es-MX", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }) : "—");
export const diaCorto = (v) => new Date(v + "T00:00:00").toLocaleDateString("es-MX", { day: "2-digit", month: "short" });
export const duracion = (ms) => (ms == null ? "—" : `${(ms / 1000).toFixed(2)} s`);
export const monedas = (n) => `${num(n)} 🪙`;
export const hoyISO = () => new Date().toISOString().slice(0, 10);
export const haceDiasISO = (d) => new Date(Date.now() - d * 864e5).toISOString().slice(0, 10);

export const ETIQUETAS_MOV = { registro: "Bono de registro", compra: "Compra", reembolso: "Reembolso", anuncio: "Anuncio", partida: "Partida", logro: "Logro", ajuste: "Ajuste admin" };

// ---------------------------------------------------------------- Estados
export function cargando(el, lineas = 4) {
  el.innerHTML = `<div aria-busy="true" aria-label="Cargando">${'<div class="cargando-linea"></div>'.repeat(lineas)}</div>`;
}

export function vacio(el, titulo = "Sin resultados", texto = "No hay información para mostrar.", icono = "🏁") {
  el.innerHTML = `<div class="estado"><div class="icono">${icono}</div><h3>${esc(titulo)}</h3><p>${esc(texto)}</p></div>`;
}

export function error(el, err, reintentar) {
  el.innerHTML = `<div class="estado error" role="alert"><div class="icono">⚠️</div><h3>No se pudo cargar</h3>
    <p>${esc(err?.message || "Ocurrió un error inesperado.")}</p>
    ${reintentar ? '<button class="btn" type="button">Reintentar</button>' : ""}</div>`;
  if (reintentar) el.querySelector("button").addEventListener("click", reintentar);
}

// ---------------------------------------------------------------- Toasts
export function toast(mensaje, tipo = "info") {
  let cont = $(".toasts");
  if (!cont) {
    cont = document.createElement("div");
    cont.className = "toasts";
    cont.setAttribute("aria-live", "polite");
    document.body.appendChild(cont);
  }
  const t = document.createElement("div");
  t.className = `toast ${tipo}`;
  t.textContent = mensaje;
  cont.appendChild(t);
  setTimeout(() => t.remove(), 4500);
}

// ---------------------------------------------------------------- Modales
export function modal({ titulo, contenido, acciones = [] }) {
  const fondo = document.createElement("div");
  fondo.className = "modal-fondo";
  fondo.innerHTML = `<div class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-titulo">
    <header><h2 id="modal-titulo">${esc(titulo)}</h2><button class="btn btn-texto btn-icono" data-cerrar aria-label="Cerrar">✕</button></header>
    <div class="cuerpo"></div><footer></footer></div>`;
  const cuerpo = $(".cuerpo", fondo);
  if (typeof contenido === "string") cuerpo.innerHTML = contenido; else cuerpo.appendChild(contenido);
  const pie = $("footer", fondo);
  if (!acciones.length) pie.remove();
  const cerrar = () => { fondo.remove(); document.removeEventListener("keydown", tecla); };
  const tecla = (e) => { if (e.key === "Escape") cerrar(); };
  for (const a of acciones) {
    const b = document.createElement("button");
    b.type = a.submit ? "submit" : "button";
    b.className = `btn ${a.clase || ""}`;
    b.textContent = a.texto;
    if (a.form) b.setAttribute("form", a.form);
    if (a.alHacerClic) b.addEventListener("click", () => a.alHacerClic(cerrar, b));
    pie.appendChild(b);
  }
  fondo.addEventListener("click", (e) => { if (e.target === fondo || e.target.closest("[data-cerrar]")) cerrar(); });
  document.addEventListener("keydown", tecla);
  document.body.appendChild(fondo);
  setTimeout(() => (fondo.querySelector("input, select, textarea, footer .btn-primario, footer .btn") || fondo).focus(), 30);
  return { cerrar, raiz: fondo };
}

/** Confirmación para operaciones críticas. Devuelve una promesa con true/false. */
export function confirmar(mensaje, { titulo = "Confirmar operación", texto = "Confirmar", peligro = false } = {}) {
  return new Promise((resolver) => {
    let decidido = false;
    const m = modal({
      titulo,
      contenido: `<p>${esc(mensaje)}</p>`,
      acciones: [
        { texto: "Cancelar", alHacerClic: (cerrar) => { decidido = true; resolver(false); cerrar(); } },
        { texto, clase: peligro ? "btn-peligro" : "btn-primario", alHacerClic: (cerrar) => { decidido = true; resolver(true); cerrar(); } },
      ],
    });
    new MutationObserver((_, obs) => {
      if (!document.body.contains(m.raiz)) { obs.disconnect(); if (!decidido) resolver(false); }
    }).observe(document.body, { childList: true });
  });
}

// ---------------------------------------------------------------- Formularios
export function datosForm(form) {
  const datos = {};
  for (const el of form.elements) {
    if (!el.name || el.disabled) continue;
    if (el.type === "checkbox") datos[el.name] = el.checked;
    else if (el.type === "number") datos[el.name] = el.value === "" ? null : Number(el.value);
    else datos[el.name] = el.value.trim();
  }
  return datos;
}

export function limpiarErrores(form) {
  $$(".campo.invalido", form).forEach((c) => c.classList.remove("invalido"));
  $$(".error-campo", form).forEach((e) => e.remove());
  $(".alerta.error", form)?.remove();
}

/** Muestra el mensaje general y los errores por campo que devuelve la API (422). */
export function mostrarErrores(form, err) {
  limpiarErrores(form);
  const general = document.createElement("div");
  general.className = "alerta error";
  general.setAttribute("role", "alert");
  general.textContent = err.message;
  form.prepend(general);
  for (const [campo, msg] of Object.entries(err.detalles || {})) {
    const input = form.elements[campo];
    const cont = input?.closest?.(".campo");
    if (!cont) continue;
    cont.classList.add("invalido");
    const p = document.createElement("div");
    p.className = "error-campo";
    p.textContent = msg;
    cont.appendChild(p);
  }
}

export async function conBoton(boton, tarea) {
  boton.disabled = true;
  boton.classList.add("cargando");
  try { return await tarea(); } finally { boton.disabled = false; boton.classList.remove("cargando"); }
}

// ---------------------------------------------------------------- Paginación y tablas
export function paginacion(el, res, irA) {
  if (!res || res.total === 0) { el.innerHTML = ""; return; }
  const ini = (res.pagina - 1) * res.limite + 1;
  const fin = Math.min(res.total, res.pagina * res.limite);
  el.innerHTML = `<span>Mostrando ${num(ini)}–${num(fin)} de ${num(res.total)}</span>
    <div class="fila">
      <button class="btn btn-sm" data-p="${res.pagina - 1}" ${res.pagina <= 1 ? "disabled" : ""}>‹ Anterior</button>
      <span>Página ${res.pagina} de ${res.totalPaginas}</span>
      <button class="btn btn-sm" data-p="${res.pagina + 1}" ${res.pagina >= res.totalPaginas ? "disabled" : ""}>Siguiente ›</button>
    </div>`;
  $$("button[data-p]", el).forEach((b) => b.addEventListener("click", () => irA(Number(b.dataset.p))));
}

/** Encabezados ordenables: <th data-orden="campo">. Alterna campo / -campo y llama a alCambiar(orden). */
export function ordenable(tabla, estado, alCambiar) {
  $$("th[data-orden]", tabla).forEach((th) => {
    th.classList.add("ordenable");
    th.tabIndex = 0;
    const campo = th.dataset.orden;
    const actual = estado.orden || "";
    th.setAttribute("aria-sort", actual === campo ? "ascending" : actual === "-" + campo ? "descending" : "none");
    const activar = () => alCambiar(estado.orden === campo ? "-" + campo : campo);
    th.addEventListener("click", activar);
    th.addEventListener("keydown", (e) => { if (e.key === "Enter") activar(); });
  });
}

export function debounce(fn, ms = 350) {
  let t;
  return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); };
}

export function badgeEstado(activo) {
  return activo ? '<span class="badge exito">Activo</span>' : '<span class="badge peligro">Inactivo</span>';
}

export function celebrarLogros(logros = []) {
  for (const l of logros) toast(`🏆 ¡Logro desbloqueado! ${l.nombre}${l.recompensa_monedas ? ` (+${l.recompensa_monedas} monedas)` : ""}`, "aviso");
}

export const ACCIONES = { login: "Inicio de sesión", logout: "Cierre de sesión", registro: "Registro", compra: "Compra", reembolso: "Reembolso",
  recompensa_anuncio: "Anuncio visto", logro_obtenido: "Logro obtenido", crear: "Creación", actualizar: "Actualización",
  eliminar: "Baja", cambiar_estado: "Cambio de estado", ajuste_monedas: "Ajuste de monedas", partida_invalida: "Partida rechazada",
  equipar_escenario: "Escenario equipado", actualizar_perfil: "Perfil actualizado", cambiar_password: "Cambio de contraseña" };
