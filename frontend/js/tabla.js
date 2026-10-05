// Tabla conectada a un endpoint paginado: filtros + orden por columna + paginación + estados.
import { get } from "./api.js";
import { $, $$, cargando, debounce, error, esc, ordenable, paginacion, vacio } from "./ui.js";

/**
 * @param {object} cfg
 *   contenedor: HTMLElement donde se dibuja
 *   endpoint: "/partidas"
 *   columnas: [{ titulo, orden?: "campo", clase?: "num", render: (fila) => html }]
 *   filtros?: HTMLFormElement (sus campos se envían como query)
 *   ordenInicial?: "-fecha", limite?: 15, vacio?: [titulo, texto]
 *   alPintar?: (res, contenedor) => void   (para enlazar botones de acciones)
 */
export function tablaPaginada(cfg) {
  const estado = { page: 1, orden: cfg.ordenInicial || "", limit: cfg.limite || 15, extra: {} };
  const cont = cfg.contenedor;
  cont.innerHTML = '<div data-tabla></div><div class="paginacion" data-paginacion></div>';
  const zona = $("[data-tabla]", cont);
  const pag = $("[data-paginacion]", cont);

  async function cargar() {
    cargando(zona, 5);
    const filtros = cfg.filtros ? Object.fromEntries(new FormData(cfg.filtros)) : {};
    try {
      const res = await get(cfg.endpoint, { ...filtros, ...estado.extra, orden: estado.orden, page: estado.page, limit: estado.limit });
      if (!res.datos.length) {
        const [t, x] = cfg.vacio || ["Sin resultados", "No hay registros que coincidan con los filtros."];
        vacio(zona, t, x, "🔎");
        pag.innerHTML = "";
        return res;
      }
      zona.innerHTML = `<div class="tabla-envoltura"><table>
        <thead><tr>${cfg.columnas.map((c) => `<th class="${c.clase || ""}" ${c.orden ? `data-orden="${c.orden}"` : ""}>${esc(c.titulo)}</th>`).join("")}</tr></thead>
        <tbody>${res.datos.map((f) => `<tr>${cfg.columnas.map((c) => `<td class="${c.clase || ""}">${c.render(f)}</td>`).join("")}</tr>`).join("")}</tbody>
      </table></div>`;
      ordenable($("table", zona), estado, (o) => { estado.orden = o; estado.page = 1; cargar(); });
      if (res.pagina) paginacion(pag, res, (p) => { estado.page = p; cargar(); });
      else pag.innerHTML = `<span>${res.datos.length} registro(s)</span>`;
      cfg.alPintar?.(res, zona);
      return res;
    } catch (e) {
      error(zona, e, cargar);
      pag.innerHTML = "";
    }
  }

  if (cfg.filtros) {
    const reiniciar = () => { estado.page = 1; cargar(); };
    $$("input[type=search], input[type=text]", cfg.filtros).forEach((i) => i.addEventListener("input", debounce(reiniciar)));
    $$("select, input[type=date], input[type=checkbox]", cfg.filtros).forEach((i) => i.addEventListener("change", reiniciar));
    cfg.filtros.addEventListener("submit", (e) => { e.preventDefault(); reiniciar(); });
  }
  cargar();
  return { recargar: cargar, estado };
}
