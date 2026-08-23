/**
 * Feedback de estado del sistema.
 *
 * Tres canales redundantes para el mismo mensaje:
 *
 *   1. #estado-polite   — role="status",  aria-live="polite"     → progreso normal
 *   2. #estado-assertive — role="alert",  aria-live="assertive"  → solo errores
 *   3. #barra-estado    — texto visible en la parte superior
 *
 * Los dos primeros son nodos permanentes del DOM: nunca se crean ni se
 * destruyen dinámicamente, solo cambia su textContent (si el nodo se inserta
 * en el mismo momento en que recibe texto, muchos lectores de pantalla no
 * llegan a anunciarlo).
 *
 * El tercero existe porque el feedback no debe ser exclusivo del lector de
 * pantalla: hace visible el estado del sistema para usuarios con resto de
 * visión, y también facilita depurar y demostrar la herramienta.
 */

let regionPolite = null;
let regionAssertive = null;
let barraVisible = null;

/*  Localiza los tres nodos. Debe llamarse una vez al arrancar cada pantalla */
function inicializarAnuncios() {
  regionPolite = document.getElementById("estado-polite");
  regionAssertive = document.getElementById("estado-assertive");
  barraVisible = document.getElementById("barra-estado");
}

/*  Escribe un mensaje en una región aria-live */
function escribirEnRegion(region, mensaje) {
  if (!region) {
    return;
  }
  region.textContent = "";
  window.setTimeout(() => {
    region.textContent = mensaje;
  }, 60);
}

/* Anuncia un mensaje de estado por todos los canales */
function anunciar(mensaje, prioridad = "polite", opciones = {}) {
  const esError = prioridad === "assertive";

  escribirEnRegion(esError ? regionAssertive : regionPolite, mensaje);

  if (barraVisible) {
    barraVisible.textContent = mensaje;
    barraVisible.classList.toggle("es-error", esError);
  }

  if (opciones.voz !== false && typeof hablar === "function") {
    hablar(mensaje);
  }
}

/* Limpia el estado mostrado */
function limpiarAnuncios() {
  if (barraVisible) {
    barraVisible.textContent = "";
    barraVisible.classList.remove("es-error");
  }
  if (regionAssertive) {
    regionAssertive.textContent = "";
  }
}
