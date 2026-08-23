/**
 * Capa opcional de síntesis de voz (toggle "Feedback auditivo").
 *
 * A tener en cuenta:
 *
 *   - Las regiones aria-live (aria-live.js) están SIEMPRE activas. Son el
 *     mecanismo que usa un lector de pantalla real (NVDA, VoiceOver, Orca) y
 *     no dependen de ninguna preferencia del usuario.
 *
 *   - Este módulo es una capa ADICIONAL construida sobre
 *     window.speechSynthesis, que narra en voz alta los mismos mensajes sin
 *     necesidad de tener un lector de pantalla instalado. Sirve para
 *     desarrollo, pruebas y demostraciones (por ejemplo, la defensa del TFG).
 *     Nunca sustituye a ARIA.
 *
 * La preferencia se guarda en localStorage: esto es una aplicación real
 * desplegada en el navegador del usuario, no un artefacto en sandbox.
 */


const CLAVE_PREFERENCIA = "feedbackAuditivo";

let activado = leerPreferencia();

function leerPreferencia() {
  try {
    return window.localStorage.getItem(CLAVE_PREFERENCIA) !== "desactivado";
  } catch (error) {
    return true;
  }
}

function guardarPreferencia(valor) {
  try {
    window.localStorage.setItem(CLAVE_PREFERENCIA, valor ? "activado" : "desactivado");
  } catch (error) {
    /* si no se puede persistir, la preferencia dura solo esta sesión */
  }
}

function soportado() {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/* ¿Está encendida la narración por voz? */
function audioActivado() {
  return activado;
}

/* Narra un mensaje por voz, si el toggle está activo */
function hablar(mensaje) {
  if (!activado || !mensaje || !soportado()) {
    return;
  }
  window.speechSynthesis.cancel();
  const locucion = new SpeechSynthesisUtterance(mensaje);
  locucion.lang = "es-ES";
  window.speechSynthesis.speak(locucion);
}

/* Detiene inmediatamente cualquier narración en curso. */
function callar() {
  if (soportado()) {
    window.speechSynthesis.cancel();
  }
}

/* Conecta el botón de toggle con este módulo */
function conectarToggle(boton, etiquetaEstado, alCambiar) {
  if (!boton) {
    return;
  }

  const pintar = () => {
    boton.setAttribute("aria-pressed", activado ? "true" : "false");
    if (etiquetaEstado) {
      etiquetaEstado.textContent = activado ? "activado" : "desactivado";
    }
  };

  if (!soportado()) {
    activado = false;
    boton.disabled = true;
    boton.setAttribute(
      "title",
      "Este navegador no dispone de síntesis de voz. El lector de pantalla sigue funcionando."
    );
  }

  pintar();

  boton.addEventListener("click", () => {
    activado = !activado;
    guardarPreferencia(activado);
    if (!activado) {
      callar();
    }
    pintar();
    if (typeof alCambiar === "function") {
      alCambiar(activado);
    }
  });
}