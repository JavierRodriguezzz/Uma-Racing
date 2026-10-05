// Pantalla CRUD genérica para administración: listado + crear/editar en modal + activar/desactivar + baja lógica.
import { del, get, patch, post, put } from "./api.js";
import { tablaPaginada } from "./tabla.js";
import { $, $$, confirmar, conBoton, datosForm, esc, limpiarErrores, modal, mostrarErrores, toast } from "./ui.js";

/**
 * cfg:
 *   contenedor, filtros (form), endpoint, nombre ("artículo"), columnas (como tablaPaginada)
 *   campos: [{ nombre, etiqueta, tipo: "text"|"number"|"select"|"textarea"|"checkbox"|"email"|"password"|"color",
 *              opciones?: [[valor, texto]], requerido?, min?, max?, maxlength?, ayuda?, soloCrear?, soloEditar? }]
 *   aFormulario?: (fila) => valores del formulario al editar
 *   aCuerpo?: (datos, esEdicion) => cuerpo JSON a enviar
 *   validar?: (datos, esEdicion) => { campo: mensaje }
 *   puedeEstado?: bool (PATCH /{id}/estado), puedeEliminar?: bool (DELETE /{id}), accionesExtra?: (fila) => html
 *   alPintarExtra?: (porId, zona, recargar) => void
 */
export function crud(cfg) {
  const columnas = [
    ...cfg.columnas,
    {
      titulo: "Acciones", clase: "num", render: (f) => `<div class="acciones">
        ${cfg.accionesExtra ? cfg.accionesExtra(f) : ""}
        <button class="btn btn-sm" data-editar="${f.id}">Editar</button>
        ${cfg.puedeEstado ? `<button class="btn btn-sm" data-estado="${f.id}">${f.activo ? "Desactivar" : "Activar"}</button>` : ""}
        ${cfg.puedeEliminar && f.activo ? `<button class="btn btn-sm btn-peligro" data-eliminar="${f.id}">Eliminar</button>` : ""}
      </div>`,
    },
  ];

  const tabla = tablaPaginada({
    contenedor: cfg.contenedor, endpoint: cfg.endpoint, filtros: cfg.filtros, columnas,
    ordenInicial: cfg.ordenInicial, limite: cfg.limite || 10, vacio: cfg.vacio,
    alPintar: (res, zona) => {
      const porId = Object.fromEntries(res.datos.map((f) => [f.id, f]));
      $$("[data-editar]", zona).forEach((b) => b.addEventListener("click", () => abrirFormulario(porId[b.dataset.editar])));
      $$("[data-estado]", zona).forEach((b) => b.addEventListener("click", () => cambiarEstado(porId[b.dataset.estado], b)));
      $$("[data-eliminar]", zona).forEach((b) => b.addEventListener("click", () => eliminar(porId[b.dataset.eliminar])));
      cfg.alPintarExtra?.(porId, zona, tabla.recargar);
    },
  });

  function campoHtml(c, valor) {
    const id = `c-${c.nombre}`;
    const req = c.requerido ? "required" : "";
    const lim = `${c.min !== undefined ? `min="${c.min}"` : ""} ${c.max !== undefined ? `max="${c.max}"` : ""} ${c.maxlength ? `maxlength="${c.maxlength}"` : ""}`;
    let input;
    if (c.tipo === "select") {
      input = `<select id="${id}" name="${c.nombre}" ${req}>${c.opciones.map(([v, t]) => `<option value="${esc(v)}" ${String(valor) === String(v) ? "selected" : ""}>${esc(t)}</option>`).join("")}</select>`;
    } else if (c.tipo === "textarea") {
      input = `<textarea id="${id}" name="${c.nombre}" ${req} ${lim}>${esc(valor ?? "")}</textarea>`;
    } else if (c.tipo === "checkbox") {
      return `<div class="campo"><label class="check"><input type="checkbox" id="${id}" name="${c.nombre}" ${valor ? "checked" : ""}> ${esc(c.etiqueta)}</label>
        ${c.ayuda ? `<span class="ayuda">${esc(c.ayuda)}</span>` : ""}</div>`;
    } else {
      input = `<input id="${id}" name="${c.nombre}" type="${c.tipo || "text"}" value="${esc(valor ?? "")}" ${req} ${lim}>`;
    }
    return `<div class="campo"><label for="${id}">${esc(c.etiqueta)}</label>${input}${c.ayuda ? `<span class="ayuda">${esc(c.ayuda)}</span>` : ""}</div>`;
  }

  function abrirFormulario(fila = null) {
    const edicion = !!fila;
    const valores = edicion ? (cfg.aFormulario ? cfg.aFormulario(fila) : fila) : {};
    const campos = cfg.campos.filter((c) => (edicion ? !c.soloCrear : !c.soloEditar));
    const form = document.createElement("form");
    form.id = "form-crud";
    form.noValidate = true;
    form.innerHTML = `<div class="form-grid">${campos.map((c) => campoHtml(c, valores[c.nombre] ?? c.defecto)).join("")}</div>`;
    const m = modal({
      titulo: `${edicion ? "Editar" : "Nuevo"} ${cfg.nombre}`,
      contenido: form,
      acciones: [{ texto: "Cancelar", alHacerClic: (cerrar) => cerrar() }, { texto: edicion ? "Guardar cambios" : "Crear", clase: "btn-primario", submit: true, form: "form-crud" }],
    });
    form.addEventListener("submit", (e) => {
      e.preventDefault();
      const datos = datosForm(form);
      limpiarErrores(form);
      const errores = {};
      for (const c of campos) {
        const v = datos[c.nombre];
        if (c.requerido && (v === "" || v === null)) errores[c.nombre] = "Este campo es obligatorio.";
        else if (c.tipo === "number" && v !== null && ((c.min !== undefined && v < c.min) || (c.max !== undefined && v > c.max)))
          errores[c.nombre] = `Debe estar entre ${c.min} y ${c.max}.`;
      }
      Object.assign(errores, cfg.validar?.(datos, edicion) || {});
      if (Object.keys(errores).length) return mostrarErrores(form, { message: "Revisa los datos marcados.", detalles: errores });
      const cuerpo = cfg.aCuerpo ? cfg.aCuerpo(datos, edicion, fila) : datos;
      conBoton($("footer .btn-primario", m.raiz), async () => {
        try {
          if (edicion) await put(`${cfg.endpoint}/${fila.id}`, cuerpo); else await post(cfg.endpoint, cuerpo);
          toast(`${cfg.nombre[0].toUpperCase() + cfg.nombre.slice(1)} ${edicion ? "actualizado" : "creado"} correctamente.`, "exito");
          m.cerrar();
          tabla.recargar();
        } catch (err) {
          mostrarErrores(form, err);
        }
      });
    });
  }

  async function cambiarEstado(fila, boton) {
    const activar = !fila.activo;
    if (!activar && !(await confirmar(`¿Desactivar "${fila.nombre || fila.titulo || fila.username}"?`, { texto: "Desactivar", peligro: true }))) return;
    boton.disabled = true;
    try {
      await patch(`${cfg.endpoint}/${fila.id}/estado`, { activo: activar });
      toast(activar ? "Registro activado." : "Registro desactivado.", "exito");
      tabla.recargar();
    } catch (e) { toast(e.message, "error"); boton.disabled = false; }
  }

  async function eliminar(fila) {
    const nombre = fila.nombre || fila.titulo || fila.username;
    if (!(await confirmar(`¿Está seguro de eliminar "${nombre}"? Se hará una baja lógica: el historial relacionado se conserva.`,
      { titulo: "Eliminar registro", texto: "Eliminar", peligro: true }))) return;
    try {
      const r = await del(`${cfg.endpoint}/${fila.id}`);
      toast(r.mensaje || "Registro eliminado.", "exito");
      tabla.recargar();
    } catch (e) { toast(e.message, "error"); }
  }

  return { nuevo: () => abrirFormulario(), recargar: tabla.recargar };
}

export { get };
