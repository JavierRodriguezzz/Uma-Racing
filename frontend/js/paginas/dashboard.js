import { get } from "../api.js";
import { grafica } from "../graficas.js";
import { iniciarPagina } from "../layout.js";
import { $, ACCIONES, cargando, diaCorto, duracion, error, esc, fechaHora, num } from "../ui.js";

const usuario = await iniciarPagina();
const panel = $("#panel");

/** Completa los 7 días aunque alguno no tenga partidas. */
function ultimos7(filas, campos) {
  const mapa = Object.fromEntries(filas.map((f) => [f.dia, f]));
  const dias = [];
  for (let i = 6; i >= 0; i--) dias.push(new Date(Date.now() - i * 864e5).toISOString().slice(0, 10));
  return { etiquetas: dias.map(diaCorto), valores: campos.map((c) => dias.map((d) => Number(mapa[d]?.[c] || 0))) };
}

const kpi = (etiqueta, valor, detalle = "", color = "") =>
  `<div class="tarjeta kpi ${color}"><span class="etiqueta">${etiqueta}</span><span class="valor">${valor}</span><span class="detalle">${detalle}</span></div>`;

async function cargar() {
  cargando(panel, 6);
  try {
    const d = await get("/dashboard");
    if (d.rol === "administrador") pintarAdmin(d); else pintarJugador(d);
  } catch (e) {
    error(panel, e, cargar);
  }
}

function pintarJugador(d) {
  const t = d.tarjetas;
  panel.innerHTML = `
    <div class="tarjeta fila" style="justify-content:space-between">
      <div><h2 style="margin:0">¡Hola, ${esc(usuario.nombre_mostrar || usuario.username)}!</h2>
        <p class="texto-2" style="margin:0">${t.partidas ? "¿Listo para otra carrera?" : "Juega tu primera carrera y gana tus primeras monedas."}</p></div>
      <div class="fila"><a class="btn btn-oro" href="/anuncios.html">Ganar monedas (${t.anuncios_restantes_hoy} hoy)</a>
        <a class="btn btn-primario" href="/jugar.html">▶ Jugar ahora</a></div>
    </div>
    <section class="grid grid-kpi" aria-label="Indicadores">
      ${kpi("Monedas", num(t.monedas), "Para gastar en la tienda", "oro")}
      ${kpi("Partidas", num(t.partidas), `${num(t.victorias)} victorias`, "pasto")}
      ${kpi("% victorias", `${t.porcentaje_victorias}%`, "Como Jugador 1", "cielo")}
      ${kpi("Mejor puntaje", num(t.mejor_puntaje), "En una sola carrera", "j2")}
      ${kpi("Ranking", t.posicion_ranking ? `#${t.posicion_ranking}` : "—", "Por puntaje total", "oro")}
      ${kpi("Logros", `${t.logros}/${t.logros_total}`, `<a href="/logros.html">Ver logros</a>`, "pasto")}
    </section>
    ${d.articulos_por_desbloquear ? `<div class="alerta info">Tienes ${d.articulos_por_desbloquear} artículo(s) por desbloquear. <a href="/tienda.html">Visita la tienda</a>.</div>` : ""}
    <section class="grid grid-2">
      <div class="tarjeta"><div class="tarjeta-titulo"><h2>Tus carreras — últimos 7 días</h2></div><div id="g-semana"></div></div>
      <div class="tarjeta"><div class="tarjeta-titulo"><h2>Últimas partidas</h2><a href="/historial.html" class="btn btn-sm">Ver historial</a></div>
        <div id="ultimas"></div></div>
    </section>`;

  const s = ultimos7(d.partidas_7d, ["partidas", "victorias"]);
  grafica($("#g-semana"), { tipo: "barra", titulo: "Partidas y victorias por día", etiquetas: s.etiquetas,
    series: [{ nombre: "Partidas", datos: s.valores[0] }, { nombre: "Victorias", datos: s.valores[1] }] });

  const ult = $("#ultimas");
  if (!d.ultimas_partidas.length) {
    ult.innerHTML = '<div class="estado"><div class="icono">🏇</div><h3>Aún no hay partidas</h3><p>Tus carreras aparecerán aquí.</p><a class="btn btn-primario" href="/jugar.html">Jugar</a></div>';
    return;
  }
  ult.innerHTML = `<div class="tabla-envoltura"><table><thead><tr><th>Fecha</th><th>Tú (J1)</th><th>Resultado</th><th class="num">Puntaje</th><th class="num">Tiempo</th></tr></thead><tbody>
    ${d.ultimas_partidas.map((p) => `<tr><td>${fechaHora(p.iniciada_en)}</td><td>${esc(p.personaje_j1)}</td>
      <td>${p.ganador === "J1" ? '<span class="badge exito">Victoria</span>' : '<span class="badge">Derrota</span>'}</td>
      <td class="num">${num(p.puntaje)}</td><td class="num">${duracion(p.duracion_ms)}</td></tr>`).join("")}
  </tbody></table></div>`;
}


function pintarAdmin(d) {
  const t = d.tarjetas;
  panel.innerHTML = `
    <section class="grid grid-kpi" aria-label="Indicadores">
      ${kpi("Jugadores activos", num(t.jugadores_activos), `${num(t.registros_7d)} registros en 7 días`, "pasto")}
      ${kpi("Partidas hoy", num(t.partidas_hoy), `${num(t.partidas_30d)} en 30 días`, "cielo")}
      ${kpi("Ventas (30 días)", num(t.ventas_monedas_30d), "Monedas gastadas en tienda", "oro")}
      ${kpi("Anuncios vistos hoy", num(t.anuncios_hoy), "Con recompensa entregada", "j2")}
      ${kpi("Monedas en circulación", num(t.monedas_en_circulacion), "Saldo total de jugadores", "oro")}
    </section>
    <section class="tarjeta"><div class="tarjeta-titulo"><h2>Alertas</h2></div>
      ${d.alertas.length ? d.alertas.map((a) => `<div class="alerta ${a.nivel === "advertencia" ? "advertencia" : "info"}">${a.nivel === "advertencia" ? "⚠️" : "ℹ️"} ${esc(a.mensaje)}</div>`).join("")
        : '<p class="texto-2" style="margin:0">✅ Sin alertas por ahora.</p>'}
    </section>
    <section class="grid grid-2">
      <div class="tarjeta"><div class="tarjeta-titulo"><h2>Partidas — últimos 7 días</h2><a class="btn btn-sm" href="/admin/reportes.html">Reportes</a></div><div id="g-semana"></div></div>
      <div class="tarjeta"><div class="tarjeta-titulo"><h2>Actividad reciente</h2><a class="btn btn-sm" href="/admin/bitacora.html">Bitácora</a></div>
        <div class="tabla-envoltura"><table><thead><tr><th>Fecha</th><th>Usuario</th><th>Operación</th><th>Registro</th></tr></thead><tbody>
        ${d.actividad_reciente.map((a) => `<tr><td>${fechaHora(a.creado_en)}</td><td>${esc(a.username || "—")}</td>
          <td>${esc(ACCIONES[a.accion] || a.accion)}</td><td class="texto-2">${esc(a.entidad)} ${esc(a.entidad_id || "")}</td></tr>`).join("")}
        </tbody></table></div></div>
    </section>`;
  const s = ultimos7(d.partidas_7d, ["partidas"]);
  grafica($("#g-semana"), { tipo: "barra", titulo: "Partidas por día", etiquetas: s.etiquetas, series: [{ nombre: "Partidas", datos: s.valores[0] }] });
}

await new Promise((r) => (window.Chart ? r() : addEventListener("load", r)));
cargar();
