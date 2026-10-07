import { get } from "../api.js";
import { grafica } from "../graficas.js";
import { iniciarPagina } from "../layout.js";
import { $, $$, cargando, diaCorto, duracion, error, esc, ETIQUETAS_MOV, haceDiasISO, hoyISO, num, toast } from "../ui.js";

await iniciarPagina();
await new Promise((r) => (window.Chart ? r() : addEventListener("load", r)));

$("#desde").value = haceDiasISO(29);
$("#hasta").value = hoyISO();
let ultimo = null;

const kpi = (etq, valor, det = "", color = "") =>
  `<div class="tarjeta kpi ${color}"><span class="etiqueta">${etq}</span><span class="valor">${valor}</span><span class="detalle">${det}</span></div>`;

function tabla(filas, cols) {
  if (!filas.length) return '<div class="estado"><p>Sin datos en el periodo.</p></div>';
  return `<div class="tabla-envoltura"><table><thead><tr>${cols.map(([t, , c]) => `<th class="${c || ""}">${t}</th>`).join("")}</tr></thead>
    <tbody>${filas.map((f) => `<tr>${cols.map(([, fn, c]) => `<td class="${c || ""}">${fn(f)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

async function cargar() {
  const rango = { desde: $("#desde").value, hasta: $("#hasta").value };
  $("#error-rango").innerHTML = "";
  if (!rango.desde || !rango.hasta) return;
  if (rango.desde > rango.hasta) {
    $("#error-rango").innerHTML = '<div class="alerta error" style="margin:12px 0 0">La fecha inicial no puede ser posterior a la fecha final.</div>';
    return;
  }
  ["#g-partidas", "#g-personajes", "#t-activos", "#g-ventas", "#t-items", "#g-economia", "#g-anuncios"].forEach((s) => cargando($(s), 4));
  try {
    const [p, v, e, m] = await Promise.all([get("/reportes/partidas", rango), get("/reportes/ventas", rango),
      get("/reportes/economia", rango), get("/reportes/monetizacion", rango)]);
    pintarMonetizacion(m);
    ultimo = { rango, p, v, e };
    const finalizadas = p.por_dia.reduce((a, d) => a + Number(d.finalizadas), 0);
    const invalidas = p.por_dia.reduce((a, d) => a + Number(d.invalidas), 0);
    $("#kpis").innerHTML =
      kpi("Partidas válidas", num(finalizadas), `${num(invalidas)} rechazadas por el servidor`, "pasto") +
      kpi("Duración promedio", duracion(p.resumen.duracion_promedio_ms), `Puntaje promedio ${num(p.resumen.puntaje_promedio)}`, "cielo") +
      kpi("Ventas", num(v.totales.compras), `${num(v.totales.monedas)} monedas · ${num(v.totales.reembolsos)} reembolsos`, "oro") +
      kpi("Monedas emitidas", num(e.totales.emitidas), `${num(e.totales.gastadas)} gastadas · neto ${num(e.totales.neto)}`, "j2");

    grafica($("#g-partidas"), { tipo: "barra", titulo: "Partidas por día", etiquetas: p.por_dia.map((d) => diaCorto(d.dia)),
      series: [{ nombre: "Válidas", datos: p.por_dia.map((d) => d.finalizadas) }, { nombre: "Jugadores distintos", datos: p.por_dia.map((d) => d.jugadores) }] });
    grafica($("#g-personajes"), { tipo: "barra-h", titulo: "Uso de personajes", etiquetas: p.por_personaje.map((x) => x.personaje),
      series: [{ nombre: "Usos", datos: p.por_personaje.map((x) => x.usos) }, { nombre: "Victorias J1", datos: p.por_personaje.map((x) => x.victorias_j1) }] });
    $("#t-activos").innerHTML = tabla(p.jugadores_mas_activos, [
      ["Jugador", (f) => esc(f.username)], ["Partidas", (f) => num(f.partidas), "num"], ["Victorias", (f) => num(f.victorias), "num"], ["Puntaje", (f) => num(f.puntaje), "num"]]);

    grafica($("#g-ventas"), { tipo: "barra", titulo: "Monedas gastadas por día", etiquetas: v.por_dia.map((d) => diaCorto(d.dia)),
      series: [{ nombre: "Monedas", datos: v.por_dia.map((d) => d.monedas) }] });
    $("#t-items").innerHTML = tabla(v.por_item, [
      ["Artículo", (f) => esc(f.item)], ["Tipo", (f) => esc(f.tipo)], ["Compras", (f) => num(f.compras), "num"], ["Monedas", (f) => num(f.monedas), "num"]]);

    grafica($("#g-economia"), { tipo: "barra-h", titulo: "Monedas por tipo de movimiento", etiquetas: e.por_tipo.map((x) => ETIQUETAS_MOV[x.tipo] || x.tipo),
      series: [{ nombre: "Monedas (negativo = gastadas)", datos: e.por_tipo.map((x) => x.monedas) }] });
    grafica($("#g-anuncios"), { tipo: "barra-h", titulo: "Vistas por anuncio", etiquetas: e.anuncios.map((x) => x.titulo),
      series: [{ nombre: "Vistas completas", datos: e.anuncios.map((x) => x.vistas) }] });
  } catch (err) {
    error($("#g-partidas"), err, cargar);
    toast(err.message, "error");
  }
}

const mxn = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });
const RAREZA = { comun: "Común", rara: "Rara", epica: "Épica" };
function pintarMonetizacion(m) {
  const a = m.apuestas;
  $("#kpis-mon").innerHTML =
    kpi("Ingresos", mxn.format(m.totales.ingresos_mxn), `${num(m.totales.ordenes)} órdenes pagadas`, "oro") +
    kpi("Apostado", num(a.apostado), `${num(a.apuestas)} apuestas · ${num(a.ganadas)} ganadas`, "j2") +
    kpi("Margen de la casa", num(a.margen), `Pagado a jugadores: ${num(a.pagado)}`, "cielo") +
    kpi("Tiradas gachapón", num(m.gacha.tiradas), `${num(m.gacha.gastado)} monedas gastadas`, "pasto");
  grafica($("#g-ingresos"), { tipo: "barra", titulo: "Ingresos por día", etiquetas: m.ingresos_por_dia.map((d) => diaCorto(d.dia)),
    series: [{ nombre: "MXN", datos: m.ingresos_por_dia.map((d) => d.monto) }], formato: (n) => mxn.format(n) });
  grafica($("#g-rarezas"), { tipo: "barra-h", titulo: "Rarezas obtenidas", etiquetas: m.gacha.rarezas.map((r) => RAREZA[r.rareza]),
    series: [{ nombre: "Premios", datos: m.gacha.rarezas.map((r) => r.cantidad) }, { nombre: "Por garantía", datos: m.gacha.rarezas.map((r) => r.por_garantia) }] });
  $("#t-paquetes").innerHTML = tabla(m.por_paquete, [
    ["Paquete", (f) => esc(f.paquete)], ["Órdenes", (f) => num(f.ordenes), "num"], ["Monedas entregadas", (f) => num(f.monedas), "num"], ["Ingresos", (f) => mxn.format(f.monto), "num"]]);
}

function exportarCSV() {
  if (!ultimo) return;
  const { rango, p, v } = ultimo;
  const lineas = [["Reporte", "Fecha", "Partidas validas", "Partidas rechazadas", "Jugadores", "Compras", "Monedas gastadas"]];
  const ventas = Object.fromEntries(v.por_dia.map((d) => [d.dia, d]));
  for (const d of p.por_dia) lineas.push(["Actividad diaria", d.dia, d.finalizadas, d.invalidas, d.jugadores, ventas[d.dia]?.compras || 0, ventas[d.dia]?.monedas || 0]);
  const csv = lineas.map((l) => l.map((x) => `"${String(x).replace(/"/g, '""')}"`).join(",")).join("\r\n");
  const a = document.createElement("a");
  a.href = URL.createObjectURL(new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" }));
  a.download = `reporte_umaracing_${rango.desde}_${rango.hasta}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

$$("#filtros input").forEach((i) => i.addEventListener("change", cargar));
$$("[data-dias]").forEach((b) => b.addEventListener("click", () => {
  $("#desde").value = haceDiasISO(Number(b.dataset.dias) - 1);
  $("#hasta").value = hoyISO();
  cargar();
}));
$("#exportar").addEventListener("click", exportarCSV);
cargar();
