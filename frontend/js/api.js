// Cliente de la API REST. El frontend nunca accede a la base de datos: todo pasa por aquí.
const CLAVE = "uma.sesion";

export class ApiError extends Error {
  constructor(status, mensaje, detalles = null) {
    super(mensaje);
    this.status = status;
    this.detalles = detalles;
  }
}

// La sesión se guarda en localStorage solo como mecanismo complementario (token + datos básicos);
// la validez real la decide el servidor en cada petición.
export const sesion = {
  obtener() {
    try { return JSON.parse(localStorage.getItem(CLAVE)) || null; } catch { return null; }
  },
  guardar(datos) {
    try { localStorage.setItem(CLAVE, JSON.stringify(datos)); } catch { /* modo privado */ }
  },
  limpiar() {
    try { localStorage.removeItem(CLAVE); } catch { /* sin acceso */ }
  },
  token() { return this.obtener()?.token || null; },
};

export async function api(metodo, ruta, cuerpo = null, query = null) {
  let url = "/api" + ruta;
  if (query) {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== null && v !== undefined && v !== "") qs.append(k, v);
    }
    if ([...qs].length) url += "?" + qs;
  }
  const opciones = { method: metodo, headers: { Accept: "application/json" } };
  const token = sesion.token();
  if (token) opciones.headers.Authorization = `Bearer ${token}`;
  if (cuerpo !== null) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }

  let respuesta;
  try {
    respuesta = await fetch(url, opciones);
  } catch {
    throw new ApiError(0, "No fue posible conectar con el servidor. Revisa tu conexión e intenta de nuevo.");
  }

  let datos = null;
  try { datos = await respuesta.json(); } catch { /* respuesta sin JSON */ }

  if (!respuesta.ok) {
    const err = datos?.error || {};
    if (respuesta.status === 401 && token && !ruta.startsWith("/auth/login")) {
      sesion.limpiar();
      const volver = encodeURIComponent(location.pathname + location.search);
      location.href = `/login.html?expirada=1&volver=${volver}`;
    }
    throw new ApiError(respuesta.status, err.mensaje || "No fue posible completar la operación.", err.detalles || null);
  }
  return datos;
}

export const get = (ruta, query) => api("GET", ruta, null, query);
export const post = (ruta, cuerpo = {}) => api("POST", ruta, cuerpo);
export const put = (ruta, cuerpo) => api("PUT", ruta, cuerpo);
export const patch = (ruta, cuerpo) => api("PATCH", ruta, cuerpo);
export const del = (ruta) => api("DELETE", ruta);
