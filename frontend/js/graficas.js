// Gráficas dinámicas con Chart.js (datos siempre provenientes de la API).
// Reglas: colores por slot fijo (máx. 3 series), barras delgadas con extremos redondeados,
// tooltip al pasar el cursor, leyenda solo con 2+ series y tabla accesible debajo.
import { esc, num } from "./ui.js";

const instancias = new Map();

function token(nombre) {
  return getComputedStyle(document.documentElement).getPropertyValue(nombre).trim();
}

function colores() {
  return {
    series: [token("--serie-1"), token("--serie-2"), token("--serie-3")],
    texto: token("--texto-2"),
    rejilla: token("--grafica-rejilla"),
    superficie: token("--superficie"),
  };
}

/**
 * @param {HTMLElement} cont  contenedor (se le agrega el canvas y la tabla)
 * @param {object} cfg  { tipo: "barra"|"linea"|"barra-h", etiquetas: [], series: [{nombre, datos}], formato }
 */
export function grafica(cont, cfg) {
  const c = colores();
  const fmt = cfg.formato || num;
  instancias.get(cont)?.destroy();

  if (!cfg.etiquetas.length) {
    cont.innerHTML = '<div class="estado"><div class="icono">📉</div><h3>Sin datos</h3><p>No hay registros en el periodo seleccionado.</p></div>';
    return;
  }
  cont.innerHTML = `<div class="grafica"><canvas role="img" aria-label="${esc(cfg.titulo || "Gráfica")}"></canvas></div>
    <details class="grafica-tabla"><summary>Ver como tabla</summary><div class="tabla-envoltura"><table>
      <thead><tr><th></th>${cfg.series.map((s) => `<th class="num">${esc(s.nombre)}</th>`).join("")}</tr></thead>
      <tbody>${cfg.etiquetas.map((e, i) => `<tr><td>${esc(e)}</td>${cfg.series.map((s) => `<td class="num">${esc(fmt(s.datos[i]))}</td>`).join("")}</tr>`).join("")}</tbody>
    </table></div></details>`;

  const horizontal = cfg.tipo === "barra-h";
  const esLinea = cfg.tipo === "linea";
  const varias = cfg.series.length > 1;
  const datasets = cfg.series.map((s, i) => ({
    label: s.nombre,
    data: s.datos.map(Number),
    backgroundColor: c.series[i],
    borderColor: esLinea ? c.series[i] : c.superficie,
    borderWidth: esLinea ? 2 : { top: 0, right: 0, bottom: 0, left: 0 },
    borderRadius: esLinea ? 0 : { topLeft: 4, topRight: 4, bottomLeft: horizontal ? 0 : 0, bottomRight: horizontal ? 4 : 0 },
    borderSkipped: horizontal ? "left" : "bottom",
    maxBarThickness: 28,
    pointRadius: esLinea ? (s.datos.length > 40 ? 0 : 3) : undefined,
    pointHoverRadius: 6,
    pointBackgroundColor: c.series[i],
    pointBorderColor: c.superficie,
    pointBorderWidth: 2,
    tension: 0.25,
    fill: false,
  }));
  if (horizontal) datasets.forEach((d) => (d.borderRadius = { topRight: 4, bottomRight: 4 }));

  const ejeValor = { beginAtZero: true, grid: { color: c.rejilla }, border: { display: false }, ticks: { color: c.texto, callback: (v) => fmt(v), maxTicksLimit: 6, precision: 0 } };
  const ejeCat = { grid: { display: false }, border: { color: c.rejilla }, ticks: { color: c.texto, maxRotation: 0, autoSkip: true, maxTicksLimit: 10 } };

  const chart = new window.Chart(cont.querySelector("canvas"), {
    type: esLinea ? "line" : "bar",
    data: { labels: cfg.etiquetas, datasets },
    options: {
      indexAxis: horizontal ? "y" : "x",
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      datasets: { bar: { categoryPercentage: 0.7, barPercentage: varias ? 0.9 : 0.8 } },
      scales: horizontal ? { x: ejeValor, y: ejeCat } : { x: ejeCat, y: ejeValor },
      plugins: {
        legend: { display: varias, position: "top", align: "end", labels: { color: c.texto, usePointStyle: true, pointStyle: "rectRounded", boxWidth: 10 } },
        tooltip: { callbacks: { label: (ctx) => ` ${ctx.dataset.label}: ${fmt(ctx.parsed[horizontal ? "x" : "y"])}` } },
      },
    },
  });
  instancias.set(cont, chart);
}
