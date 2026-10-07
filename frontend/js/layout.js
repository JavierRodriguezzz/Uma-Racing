// Estructura común: barra lateral según el rol, barra superior con monedas y cierre de sesión.
// Cada página declara en <body>: data-pagina, data-titulo y data-roles ("jugador", "administrador" o ambos).
import { get, post, sesion } from "./api.js";
import { contar, entrada, listo } from "./fx.js";
import { $, $$, confirmar, esc, num, toast } from "./ui.js";

const I = {
  inicio: '<path d="M3 11l9-8 9 8v9a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z"/>',
  jugar: '<path d="M6 4l14 8-14 8z"/>',
  tienda: '<path d="M4 7h16l-1.5 12a2 2 0 0 1-2 2h-9a2 2 0 0 1-2-2zM9 7a3 3 0 0 1 6 0"/>',
  anuncio: '<path d="M3 10v4h4l5 4V6L7 10zM16 8a5 5 0 0 1 0 8M19 5a9 9 0 0 1 0 14"/>',
  ranking: '<path d="M8 21V11H3v10zM15 21V4h-5v17zM21 21v-7h-5v7z"/>',
  logro: '<path d="M8 21h8M12 17v4M7 4h10v5a5 5 0 0 1-10 0zM7 6H4a3 3 0 0 0 3 4M17 6h3a3 3 0 0 1-3 4"/>',
  historial: '<path d="M3 12a9 9 0 1 0 3-6.7L3 8M3 3v5h5M12 7v5l3 3"/>',
  perfil: '<path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21a8 8 0 0 1 16 0"/>',
  usuarios: '<path d="M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM2 21a7 7 0 0 1 14 0M17 3.5a4 4 0 0 1 0 7.5M22 21a7 7 0 0 0-4-6.3"/>',
  items: '<path d="M21 8l-9-5-9 5 9 5zM3 8v8l9 5 9-5V8M12 13v8"/>',
  ventas: '<path d="M3 3h18v4H3zM5 7v13h14V7M9 11h6"/>',
  reportes: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>',
  bitacora: '<path d="M6 3h11l3 3v15H6zM9 9h8M9 13h8M9 17h5"/>',
  salir: '<path d="M15 4h4a1 1 0 0 1 1 1v14a1 1 0 0 1-1 1h-4M10 17l5-5-5-5M15 12H3"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
  moneda: '<circle cx="12" cy="12" r="8"/><path d="M12 7v10M9.5 9.5h3.75a1.75 1.75 0 0 1 0 3.5h-2.5a1.75 1.75 0 0 0 0 3.5H14.5"/>',
  apuesta: '<rect x="3" y="3" width="18" height="18" rx="3"/><circle cx="8" cy="8" r="1.3" fill="currentColor"/><circle cx="16" cy="16" r="1.3" fill="currentColor"/><circle cx="12" cy="12" r="1.3" fill="currentColor"/>',
  gacha: '<circle cx="12" cy="9" r="6"/><path d="M6 9h12M7 15l-1 6h12l-1-6M10 18h4"/>',
};
export const icono = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${I[n]}</svg>`;

const NAV = {
  jugador: [
    ["Mi juego", [["dashboard", "Inicio", "/dashboard.html", "inicio"], ["jugar", "Jugar", "/jugar.html", "jugar"],
      ["tienda", "Tienda", "/tienda.html", "tienda"]]],
    ["Monedas", [["monedas", "Comprar monedas", "/monedas.html", "moneda"], ["anuncios", "Ver anuncios", "/anuncios.html", "anuncio"],
      ["apuestas", "Apuestas", "/apuestas.html", "apuesta", true], ["gacha", "Gachapón", "/gacha.html", "gacha", true]]],
    ["Competencia", [["ranking", "Ranking", "/ranking.html", "ranking"], ["logros", "Logros", "/logros.html", "logro"],
      ["historial", "Historial", "/historial.html", "historial"]]],
    ["Cuenta", [["perfil", "Perfil", "/perfil.html", "perfil"]]],
  ],
  administrador: [
    ["General", [["dashboard", "Dashboard", "/dashboard.html", "inicio"], ["reportes", "Reportes", "/admin/reportes.html", "reportes"],
      ["ranking", "Ranking", "/ranking.html", "ranking"]]],
    ["Administración", [["usuarios", "Usuarios", "/admin/usuarios.html", "usuarios"], ["items", "Artículos", "/admin/items.html", "items"],
      ["admin-anuncios", "Anuncios", "/admin/anuncios.html", "anuncio"], ["admin-logros", "Logros", "/admin/logros.html", "logro"],
      ["ventas", "Ventas", "/admin/ventas.html", "ventas"], ["paquetes", "Paquetes de monedas", "/admin/paquetes.html", "moneda"],
      ["admin-gacha", "Gachapón", "/admin/gacha.html", "gacha"], ["bitacora", "Bitácora", "/admin/bitacora.html", "bitacora"]]],
    ["Cuenta", [["perfil", "Perfil", "/perfil.html", "perfil"]]],
  ],
};

let usuarioActual = null;

export function actualizarMonedas(n) {
  contar($("#saldo"), Number(n));
  if (usuarioActual) usuarioActual.monedas = n;
}

/** Verifica la sesión con el servidor, arma la interfaz y devuelve el usuario. */
export async function iniciarPagina() {
  const b = document.body;
  const roles = (b.dataset.roles || "jugador administrador").split(" ");
  if (!sesion.token()) {
    location.href = `/login.html?volver=${encodeURIComponent(location.pathname + location.search)}`;
    return new Promise(() => {});
  }
  let usuario;
  try {
    usuario = await get("/auth/me");
  } catch (e) {
    if (e.status !== 401) document.body.innerHTML = `<div class="estado error"><h3>No fue posible conectar con el servidor</h3><p>${esc(e.message)}</p><button class="btn" onclick="location.reload()">Reintentar</button></div>`;
    return new Promise(() => {});
  }
  usuarioActual = usuario;
  sesion.guardar({ ...sesion.obtener(), usuario: { id: usuario.id, username: usuario.username, rol: usuario.rol } });
  montar(usuario);
  if (!roles.includes(usuario.rol)) {
    $("#contenido").innerHTML = `<div class="tarjeta estado"><div class="icono">🔒</div><h3>Sin permisos</h3>
      <p>Esta sección no está disponible para tu tipo de cuenta.</p><a class="btn btn-primario" href="/dashboard.html">Ir al inicio</a></div>`;
    return new Promise(() => {});
  }
  return usuario;
}

function montar(usuario) {
  const contenido = $("#contenido");
  const pagina = document.body.dataset.pagina;
  const titulo = document.body.dataset.titulo || document.title;
  const grupos = NAV[usuario.rol] || NAV.jugador;
  const app = document.createElement("div");
  app.className = "app";
  app.innerHTML = `
    <aside class="sidebar" id="sidebar" aria-label="Navegación principal">
      <div class="marquesina">
        <a class="logo" href="/dashboard.html"><img src="/img/logo.png" alt=""><span>UMA<br>RACING<small>${usuario.rol === "administrador" ? "ADMIN MODE" : "ONLINE"}</small></span></a>
        <div class="focos" aria-hidden="true">${"<i></i>".repeat(11)}</div>
      </div>
      <nav class="nav">${grupos.map(([g, links]) => `<div class="nav-grupo">${g}</div>` + links.map(([id, txt, href, ic, nuevo]) =>
        `<a href="${href}" class="${id === pagina ? "activo" : ""}" ${id === pagina ? 'aria-current="page"' : ""}>${icono(ic)}${txt}${nuevo ? '<span class="nuevo">NEW</span>' : ""}</a>`).join("")).join("")}
        <div class="nav-grupo"></div><a href="#" id="salir">${icono("salir")}Cerrar sesión</a>
      </nav>
    </aside>
    <div class="principal">
      <header class="topbar">
        <button class="btn btn-texto btn-icono btn-menu" id="btn-menu" aria-label="Abrir menú" aria-controls="sidebar">${icono("menu")}</button>
        <h1>${esc(titulo)}</h1>
        ${usuario.rol === "jugador" ? `<a class="monedas" href="/monedas.html" title="Mis monedas · comprar más"><span id="saldo" data-valor="${usuario.monedas}">${num(usuario.monedas)}</span></a>` : ""}
        <div class="usuario-menu"><span class="nombre texto-2">${esc(usuario.nombre_mostrar || usuario.username)}</span>
          <a class="avatar" href="/perfil.html" title="Mi perfil">${esc((usuario.nombre_mostrar || usuario.username)[0].toUpperCase())}</a></div>
      </header>
    </div>`;
  document.body.prepend(app);
  $(".principal", app).appendChild(contenido);
  contenido.hidden = false;
  // Entrada escalonada de los paneles de la página (los que se pintan después usan entrada() por su cuenta)
  listo().then(() => entrada($$(":scope > *", contenido)));

  const sidebar = $("#sidebar");
  $("#btn-menu").addEventListener("click", (e) => { e.stopPropagation(); sidebar.classList.toggle("abierta"); });
  document.addEventListener("click", (e) => { if (sidebar.classList.contains("abierta") && !sidebar.contains(e.target)) sidebar.classList.remove("abierta"); });
  $("#salir").addEventListener("click", async (e) => {
    e.preventDefault();
    if (!(await confirmar("¿Deseas cerrar tu sesión?", { titulo: "Cerrar sesión", texto: "Cerrar sesión" }))) return;
    try { await post("/auth/logout"); } catch { /* aunque falle, se limpia localmente */ }
    sesion.limpiar();
    location.href = "/login.html?salida=1";
  });
}

export function aviso(mensaje, tipo = "info") { toast(mensaje, tipo); }
