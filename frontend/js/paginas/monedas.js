import { get, post } from "../api.js";
import { entrada, estallido, listo } from "../fx.js";
import { actualizarMonedas, iniciarPagina } from "../layout.js";
import { tablaPaginada } from "../tabla.js";
import { $, $$, cargando, error, esc, fechaHora, num, toast } from "../ui.js";

await iniciarPagina();
const mxn = new Intl.NumberFormat("es-MX", { style: "currency", currency: "MXN" });

let info = null;       // paquetes + entorno
let orden = null;      // orden pendiente creada por el servidor
let clienteGP = null;  // google.payments.api.PaymentsClient

// ---------------------------------------------------------------- Google Pay
const BASE = { apiVersion: 2, apiVersionMinor: 0 };
const TARJETA = {
  type: "CARD",
  parameters: { allowedAuthMethods: ["PAN_ONLY", "CRYPTOGRAM_3DS"], allowedCardNetworks: ["VISA", "MASTERCARD", "AMEX"] },
};
const TARJETA_TOKEN = {
  ...TARJETA,
  // En TEST se usa la pasarela de ejemplo de Google; en producción va la pasarela real (Stripe, Conekta...)
  tokenizationSpecification: { type: "PAYMENT_GATEWAY", parameters: { gateway: "example", gatewayMerchantId: "exampleGatewayMerchantId" } },
};

async function prepararGooglePay() {
  const nota = $("#gpay-nota");
  const esperar = (ms) => new Promise((r) => setTimeout(r, ms));
  for (let i = 0; i < 30 && !window.google?.payments?.api; i++) await esperar(100);
  if (!window.google?.payments?.api) {
    nota.textContent = "No se pudo cargar Google Pay (¿sin internet o bloqueado?). Puedes simular el pago de prueba.";
    $("#simular").hidden = info.entorno !== "TEST";
    return;
  }
  clienteGP = new google.payments.api.PaymentsClient({ environment: info.entorno === "PRODUCTION" ? "PRODUCTION" : "TEST" });
  try {
    const r = await clienteGP.isReadyToPay({ ...BASE, allowedPaymentMethods: [TARJETA] });
    if (!r.result) throw new Error();
    const boton = clienteGP.createButton({ onClick: pagarConGoogle, buttonColor: "black", buttonType: "pay", buttonSizeMode: "fill", buttonLocale: "es" });
    $("#gpay").replaceChildren(boton);
    nota.textContent = info.entorno === "TEST" ? "Modo de prueba: elige cualquiera de las tarjetas de prueba de Google. No se cobra nada." : "";
    $("#simular").hidden = info.entorno !== "TEST";
  } catch {
    nota.textContent = "Google Pay no está disponible en este navegador. En modo de prueba puedes simular el pago.";
    $("#simular").hidden = info.entorno !== "TEST";
  }
}

function pagarConGoogle() {
  if (!orden) return toast("Elige un paquete primero.", "aviso");
  // loadPaymentData debe llamarse directamente en el clic (el navegador bloquea la ventana si no)
  clienteGP.loadPaymentData({
    ...BASE,
    allowedPaymentMethods: [TARJETA_TOKEN],
    transactionInfo: orden.transaccion,
    merchantInfo: { merchantName: info.comercio, ...(info.merchant_id ? { merchantId: info.merchant_id } : {}) },
  })
    .then((paymentData) => confirmar(paymentData))
    .catch((e) => { if (e?.statusCode !== "CANCELED") toast("Google Pay no pudo completar el pago.", "error"); });
}

function simularPago() {
  // Mismo formato que devuelve Google Pay en modo TEST (solo disponible en TEST)
  confirmar({
    apiVersion: 2, apiVersionMinor: 0,
    paymentMethodData: { type: "CARD", description: "Visa •••• 1111 (prueba)", info: { cardNetwork: "VISA", cardDetails: "1111" },
      tokenizationData: { type: "PAYMENT_GATEWAY", token: "examplePaymentMethodToken" } },
  });
}

async function confirmar(paymentData) {
  try {
    const r = await post(`/pagos/ordenes/${encodeURIComponent(orden.folio)}/confirmar`, paymentData);
    actualizarMonedas(r.saldo);
    toast(`¡Listo! +${num(r.monedas)} monedas (${r.folio})`, "exito");
    estallido($("#saldo"), ["#ffd23f", "#fff3b0", "#ff8a3d"], 36);
    orden = null;
    $("#caja").hidden = true;
    $$("[data-paquete]").forEach((b) => b.setAttribute("aria-pressed", "false"));
    historial.recargar();
  } catch (e) {
    toast(e.message, "error");
    if (e.status === 409) seleccionar(Number($("[data-paquete][aria-pressed=true]")?.dataset.paquete));
  }
}

// ---------------------------------------------------------------- Paquetes
function pila(total) {
  const n = Math.min(6, Math.max(2, Math.round(Math.log2(total / 100)) + 2));
  return Array.from({ length: n }, (_, i) => `<span style="height:${30 + ((i * 37) % 50)}px"></span>`).join("");
}

async function cargarPaquetes() {
  cargando($("#paquetes"), 4);
  try {
    info = await get("/paquetes");
    $("#entorno").textContent = `GOOGLE PAY · ${info.entorno}`;
    $("#paquetes").innerHTML = info.datos.map((p) => `
      <article class="tarjeta paquete ${p.destacado ? "destacado" : ""}">
        ${p.destacado ? '<span class="cinta">MEJOR VALOR</span>' : ""}
        <div class="pila-monedas" aria-hidden="true">${pila(p.total)}</div>
        <div class="cantidad">${num(p.total)}</div>
        <div class="bonus">${p.bonus ? `${num(p.monedas)} + ${num(p.bonus)} DE REGALO` : "&nbsp;"}</div>
        <div><strong>${esc(p.nombre)}</strong></div>
        <div class="precio-mxn">${mxn.format(p.precio_mxn)}</div>
        <button class="btn btn-oro" style="width:100%" data-paquete="${p.id}" aria-pressed="false">Elegir</button>
      </article>`).join("");
    entrada($$("#paquetes > *"));
    $$("[data-paquete]").forEach((b) => b.addEventListener("click", () => seleccionar(Number(b.dataset.paquete))));
    prepararGooglePay();
  } catch (e) { error($("#paquetes"), e, cargarPaquetes); }
}

async function seleccionar(id) {
  const p = info.datos.find((x) => x.id === id);
  if (!p) return;
  $$("[data-paquete]").forEach((b) => b.setAttribute("aria-pressed", String(Number(b.dataset.paquete) === id)));
  $$("[data-paquete]").forEach((b) => (b.textContent = Number(b.dataset.paquete) === id ? "✔ Elegido" : "Elegir"));
  try {
    orden = await post("/pagos/ordenes", { paquete_id: id });   // el SERVIDOR fija el monto
    $("#caja").hidden = false;
    $("#orden-folio").textContent = orden.folio;
    $("#caja-nombre").textContent = p.nombre;
    $("#caja-monedas").textContent = `${num(orden.monedas)} monedas`;
    $("#caja-precio").textContent = `${mxn.format(orden.monto)} ${orden.moneda}`;
    $("#caja-expira").textContent = `La orden vence ${fechaHora(orden.expira_en)}.`;
    $("#caja").scrollIntoView({ behavior: "smooth", block: "nearest" });
  } catch (e) { toast(e.message, "error"); }
}

$("#simular").addEventListener("click", () => (orden ? simularPago() : toast("Elige un paquete primero.", "aviso")));

// ---------------------------------------------------------------- Tiempo de juego
async function tiempo() {
  try {
    const t = await get("/tiempo-juego/resumen");
    $("#tiempo-reglas").textContent = `Cada ${t.bloque_segundos / 60} minutos de juego activo te dan ${t.monedas_por_bloque} monedas (máximo ${t.limite_diario} al día). Llevas ${num(t.minutos_totales)} minutos jugados en total.`;
    $("#tiempo-hoy").textContent = `${t.monedas_hoy} / ${t.limite_diario}`;
    await listo();
    const ancho = `${Math.min(100, (100 * t.monedas_hoy) / t.limite_diario)}%`;
    if (window.anime) window.anime({ targets: "#tiempo-barra", width: ["0%", ancho], duration: 900, easing: "easeOutCubic" });
    else $("#tiempo-barra").style.width = ancho;
  } catch { /* el bloque es informativo */ }
}

// ---------------------------------------------------------------- Historial
const ESTADO = { pagada: "exito", pendiente: "aviso", cancelada: "", expirada: "peligro" };
const historial = tablaPaginada({
  contenedor: $("#historial"), endpoint: "/pagos/ordenes", ordenInicial: "-fecha", limite: 8,
  vacio: ["Sin compras", "Aquí aparecerán tus compras de monedas."],
  columnas: [
    { titulo: "Folio", render: (o) => `<code>${esc(o.folio)}</code>` },
    { titulo: "Fecha", orden: "fecha", render: (o) => fechaHora(o.creada_en) },
    { titulo: "Paquete", render: (o) => esc(o.paquete) },
    { titulo: "Monedas", clase: "num", render: (o) => num(o.monedas) },
    { titulo: "Monto", orden: "monto", clase: "num", render: (o) => mxn.format(o.monto) },
    { titulo: "Tarjeta", render: (o) => esc(o.red_tarjeta || "—") },
    { titulo: "Estado", render: (o) => `<span class="badge ${ESTADO[o.estado]}">${esc(o.estado)}</span> <span class="texto-3" style="font-size:11px">${esc(o.entorno)}</span>` },
  ],
});

cargarPaquetes();
tiempo();
