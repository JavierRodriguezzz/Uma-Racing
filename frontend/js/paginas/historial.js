import { get } from "../api.js";
import { grafica } from "../graficas.js";
import { iniciarPagina } from "../layout.js";
import { tablaPaginada } from "../tabla.js";
import { $, $$, cargando, diaCorto, duracion, error, esc, ETIQUETAS_MOV, fechaHora, haceDiasISO, hoyISO, num } from "../ui.js";

await iniciarPagina();

// ---- Estadísticas con rango de fechas (por defecto, últimos 30 días)
$("#s-desde").value = haceDiasISO(29);
$("#s-hasta").value = hoyISO();
async function estadisticas() {
  const gd = $("#g-dias"), gp = $("#g-personajes");
  cargando(gd, 5); cargando(gp, 5);
  try {
    const r = await get("/perfil/estadisticas", Object.fromEntries(new FormData($("#f-stats"))));
    grafica(gd, { tipo: "linea", titulo: "Partidas y victorias por día", etiquetas: r.por_dia.map((d) => diaCorto(d.dia)),
      series: [{ nombre: "Partidas", datos: r.por_dia.map((d) => d.partidas) }, { nombre: "Victorias", datos: r.por_dia.map((d) => d.victorias) }] });
    grafica(gp, { tipo: "barra-h", titulo: "Partidas y victorias por personaje", etiquetas: r.por_personaje.map((p) => p.personaje),
      series: [{ nombre: "Partidas", datos: r.por_personaje.map((p) => p.partidas) }, { nombre: "Victorias", datos: r.por_personaje.map((p) => p.victorias) }] });
  } catch (e) { error(gd, e, estadisticas); gp.innerHTML = ""; }
}
$$("#f-stats input").forEach((i) => i.addEventListener("change", estadisticas));

// ---- Tablas
tablaPaginada({
  contenedor: $("#t-partidas"), endpoint: "/partidas", filtros: $("#f-partidas"), ordenInicial: "-fecha", limite: 10,
  vacio: ["Sin partidas", "Juega una carrera para verla aquí."],
  columnas: [
    { titulo: "Fecha", orden: "fecha", render: (p) => fechaHora(p.iniciada_en) },
    { titulo: "Tú (J1)", render: (p) => esc(p.personaje_j1) },
    { titulo: "Invitado (J2)", render: (p) => esc(p.personaje_j2) },
    { titulo: "Escenario", render: (p) => esc(p.escenario) },
    { titulo: "Resultado", render: (p) => p.estado === "invalida" ? `<span class="badge peligro" title="${esc(p.motivo_invalida)}">Rechazada</span>`
        : p.ganador === "J1" ? '<span class="badge exito">Victoria</span>' : '<span class="badge">Derrota</span>' },
    { titulo: "Tiempo", orden: "duracion", clase: "num", render: (p) => duracion(p.duracion_ms) },
    { titulo: "Puntaje", orden: "puntaje", clase: "num", render: (p) => num(p.puntaje) },
    { titulo: "Monedas", orden: "monedas", clase: "num", render: (p) => (p.monedas_ganadas ? `+${num(p.monedas_ganadas)}` : "0") },
  ],
});

tablaPaginada({
  contenedor: $("#t-mov"), endpoint: "/perfil/movimientos", filtros: $("#f-mov"), ordenInicial: "-fecha", limite: 10,
  columnas: [
    { titulo: "Fecha", orden: "fecha", render: (m) => fechaHora(m.creado_en) },
    { titulo: "Tipo", render: (m) => `<span class="badge ${m.monto > 0 ? "exito" : "aviso"}">${esc(ETIQUETAS_MOV[m.tipo] || m.tipo)}</span>` },
    { titulo: "Descripción", render: (m) => esc(m.descripcion) },
    { titulo: "Monto", orden: "monto", clase: "num", render: (m) => `<strong style="color:var(${m.monto > 0 ? "--exito" : "--peligro"})">${m.monto > 0 ? "+" : ""}${num(m.monto)}</strong>` },
    { titulo: "Saldo", clase: "num", render: (m) => num(m.saldo_nuevo) },
  ],
});

tablaPaginada({
  contenedor: $("#t-compras"), endpoint: "/compras", ordenInicial: "-fecha", limite: 10,
  vacio: ["Sin compras", "Los artículos que compres en la tienda aparecerán aquí."],
  columnas: [
    { titulo: "Folio", orden: "folio", render: (c) => `<code>${esc(c.folio)}</code>` },
    { titulo: "Fecha", orden: "fecha", render: (c) => fechaHora(c.creada_en) },
    { titulo: "Artículo", orden: "item", render: (c) => esc(c.item) },
    { titulo: "Precio", orden: "precio", clase: "num", render: (c) => num(c.precio_pagado) },
    { titulo: "Estado", render: (c) => c.estado === "completada" ? '<span class="badge exito">Completada</span>'
        : `<span class="badge aviso" title="${esc(c.motivo_reembolso || "")}">Reembolsada</span>` },
  ],
});

await new Promise((r) => (window.Chart ? r() : addEventListener("load", r)));
estadisticas();
