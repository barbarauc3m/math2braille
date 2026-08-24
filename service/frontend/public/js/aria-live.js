/**
 * Feedback de estado del sistema.
 *
 * Un único canal accesible para todo el feedback, más su reflejo visual:
 *
 *   1. #estado-assertive — role="alert", aria-live="assertive" → todo el feedback
 *   2. #barra-estado     — texto visible en la parte superior
 *
 * Antes había también un canal "polite" para el progreso normal. Se ha
 * retirado: con aria-live="polite" el lector de pantalla ENCOLA los
 * mensajes en vez de interrumpir, así que si el usuario cambia de elemento
 * o de página más rápido de lo que tarda en leerse cada mensaje, se queda
 * escuchando el anuncio de algo que ya ha dejado de estar seleccionado.
 * Con "assertive" cada mensaje nuevo corta al anterior: lo que se oye
 * corresponde siempre al elemento o acción actual, nunca a uno anterior.
 *
 * El nodo es permanente: existe desde la carga de la página y nunca se
 * crea ni se destruye dinámicamente, solo cambia su textContent (si el
 * nodo se inserta en el mismo momento en que recibe texto, muchos
 * lectores de pantalla no llegan a anunciarlo).
 */

let regionAssertive = null;
let barraVisible = null;

/** Timer de una escritura diferida pendiente (ver escribirEnRegion). */
let escrituraPendiente = null;

/* Localiza los nodos. Debe llamarse una vez al arrancar cada pantalla */
function inicializarAnuncios() {
  regionAssertive = document.getElementById("estado-assertive");
  barraVisible = document.getElementById("barra-estado");
}

/*
 * Escribe el mensaje en la región aria-live.
 *
 * Dos casos:
 *
 *   - Texto distinto del que ya había: se escribe AL INSTANTE, sin demora.
 *     Esto es lo que hace que el anuncio corte de verdad lo que se
 *     estuviera diciendo: cualquier retardo aquí es tiempo de más que el
 *     lector sigue hablando de un elemento que ya no es el actual.
 *
 *   - Texto idéntico al que ya había (p. ej. dos errores iguales
 *     seguidos): hace falta vaciar y reescribir con un pequeño retardo
 *     para forzar la mutación, porque si el DOM no cambia el lector no
 *     vuelve a anunciarlo.
 *
 * En ambos casos se cancela cualquier escritura diferida pendiente de una
 * llamada anterior. Sin esto, dos anuncios seguidos en menos de 60ms
 * generaban dos escrituras reales al DOM (una por cada llamada), y el
 * lector las anunciaba las dos en orden -- primero la vieja, luego la
 * actual -- aunque la región fuera assertive: assertive interrumpe lo que
 * se está diciendo en el momento de la mutación, pero no evita que se
 * programen varias mutaciones reales una detrás de otra.
 */
function escribirEnRegion(mensaje) {
  if (!regionAssertive) {
    return;
  }

  if (escrituraPendiente !== null) {
    window.clearTimeout(escrituraPendiente);
    escrituraPendiente = null;
  }

  if (regionAssertive.textContent === mensaje) {
    regionAssertive.textContent = "";
    escrituraPendiente = window.setTimeout(() => {
      regionAssertive.textContent = mensaje;
      escrituraPendiente = null;
    }, 60);
    return;
  }

  regionAssertive.textContent = mensaje;
}

/**
 * Anuncia un mensaje de estado.
 *
 * `prioridad` ya no elige a qué región va el mensaje (solo hay una): se
 * conserva únicamente para decidir el estilo VISUAL de la barra superior
 * (resalte rojo en los errores).
 */
function anunciar(mensaje, prioridad = "polite") {
  const esError = prioridad === "assertive";

  escribirEnRegion(mensaje);

  if (barraVisible) {
    barraVisible.textContent = mensaje;
    barraVisible.classList.toggle("es-error", esError);
  }
}

/* Limpia el estado mostrado */
function limpiarAnuncios() {
  if (escrituraPendiente !== null) {
    window.clearTimeout(escrituraPendiente);
    escrituraPendiente = null;
  }
  if (barraVisible) {
    barraVisible.textContent = "";
    barraVisible.classList.remove("es-error");
  }
  if (regionAssertive) {
    regionAssertive.textContent = "";
  }
}
