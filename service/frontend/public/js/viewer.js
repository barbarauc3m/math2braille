/*Lógica del visor y del editor (viewer.xhtml).

El visor muestra el contenido del documento y las fórmulas 
solicitadas bajo demanda. */

const NS_XHTML = "http://www.w3.org/1999/xhtml";


/* Referencias al DOM */
const nombreDocumento = document.getElementById("nombre-documento");
const indicadorPagina = document.getElementById("indicador-pagina");
const btnAnterior = document.getElementById("btn-anterior");
const btnSiguiente = document.getElementById("btn-siguiente");
const btnCerrarDocumento = document.getElementById("btn-cerrar-documento");
const btnOcrAutomatico = document.getElementById("btn-ocr-automatico");
const contenedorPagina = document.getElementById("pagina-contenido");

const panel = document.getElementById("panel-formula");
const panelTitulo = document.getElementById("panel-titulo");
const panelMeta = document.getElementById("panel-meta");
const panelCargando = document.getElementById("panel-cargando");
const panelAviso = document.getElementById("panel-aviso");
const panelContenido = document.getElementById("panel-contenido");
const panelVistaPrevia = document.getElementById("panel-vista-previa");
const editorMathml = document.getElementById("editor-mathml");
const btnGuardar = document.getElementById("btn-guardar");
const btnCerrarPanel = document.getElementById("btn-cerrar-panel");


/* Estado de la pantalla */
const parametros = new URLSearchParams(window.location.search);
const documentoId = Number.parseInt(parametros.get("documento_id"), 10);
let paginaActual = Number.parseInt(parametros.get("pagina"), 10) || 1;

let documento = null;
let formulasPagina = [];
let seleccionada = null;

// "Procesar todas": si se activa, cada página cargada dispara el
// procesamiento en bloque de sus fórmulas pendientes (sin esperar a
// que el usuario las seleccione una a una). Vive solo en memoria: no
// persiste entre sesiones ni recargas de esta pestaña.
let ocrAutomatico = false;
// Evita solapar dos lotes a la vez (p.ej. si el usuario cambia de
// página muy rápido con el ajuste activado).
let procesandoLote = false;


/* Utilidades de MathML */
function parsearMathml(cadena) {
  if (!cadena) {
    return null;
  }
  const envuelto = '<div xmlns="' + NS_XHTML + '">' + cadena + "</div>";
  let arbol;
  try {
    arbol = new DOMParser().parseFromString(envuelto, "application/xhtml+xml");
  } catch (error) {
    return null;
  }
  if (!arbol.documentElement || arbol.querySelector("parsererror")) {
    return null;
  }

  const fragmento = document.createDocumentFragment();
  Array.prototype.forEach.call(arbol.documentElement.childNodes, (hijo) => {
    fragmento.appendChild(document.importNode(hijo, true));
  });
  return fragmento;
}

function pintarMathml(contenedor, mathml) {
  contenedor.textContent = "";
  const nodos = parsearMathml(mathml);
  if (nodos) {
    contenedor.appendChild(nodos);
    return true;
  }
  contenedor.textContent = mathml || "";
  return false;
}


/* Regiones de fórmula */
function refrescarRegion(entrada, activa) {
  const { boton, formula, numero } = entrada;
  const procesada = Boolean(formula.mathml);

  boton.classList.toggle("procesada", procesada);
  boton.classList.toggle("activa", activa);

  let estado = "Sin procesar";
  if (activa) {
    estado = "Seleccionada.";
  } else if (procesada) {
    estado = "Procesada.";
  }
  boton.setAttribute("aria-label", "Fórmula " + numero + ". " + estado);
  boton.setAttribute("aria-expanded", activa ? "true" : "false");

  if (procesada) {
    pintarMathml(boton, formula.mathml);
  } else {
    boton.textContent = "…";
  }
}

function crearRegion(formula, numero) {
  const boton = document.createElement("button");
  boton.type = "button";
  boton.className = "formula-region";
  boton.dataset.formulaId = String(formula.id);
  boton.setAttribute("aria-controls", "panel-formula");

  const entrada = { formula, numero, boton };
  boton.addEventListener("click", () => seleccionarFormula(numero));

  refrescarRegion(entrada, false);
  return entrada;
}


/* Carga y pintado de la página */
async function cargarDocumento() {
  if (!Number.isInteger(documentoId) || documentoId <= 0) {
    contenedorPagina.textContent = "";
    const aviso = document.createElement("p");
    aviso.className = "panel__aviso";
    aviso.textContent =
      "No se ha indicado ningún documento. Vuelve a la pantalla de inicio y abre uno.";
    contenedorPagina.appendChild(aviso);
    anunciar("No se ha indicado ningún documento válido.", "assertive");
    return;
  }

  try {
    documento = await abrirDocumento(documentoId);
  } catch (error) {
    anunciar("No se ha podido abrir el documento. " + error.mensaje, "assertive");
    return;
  }

  document.title = documento.nombre_archivo + " — math2braille";
  nombreDocumento.textContent = documento.nombre_archivo;

  const total = documento.num_paginas || 1;
  if (paginaActual < 1) {
    paginaActual = 1;
  }
  if (paginaActual > total) {
    paginaActual = total;
  }

  await cargarPagina();
}

async function cargarPagina() {
  const total = documento.num_paginas || 1;
  indicadorPagina.textContent = "Página " + paginaActual + " de " + total;
  btnAnterior.disabled = paginaActual <= 1;
  btnSiguiente.disabled = paginaActual >= total;

  contenedorPagina.textContent = "";
  const cargando = document.createElement("p");
  cargando.className = "pagina__vacia";
  cargando.textContent = "Cargando contenido de la página…";
  contenedorPagina.appendChild(cargando);

  // No se anuncia "Cargando la página..." aquí: sería un segundo mensaje
  // por cada navegación, hablado casi a la vez que el definitivo de más
  // abajo -- con assertive el segundo corta al primero de todos modos, así
  // que solo consigue que el primero se oiga a medias. Un único mensaje al
  // terminar de cargar es más claro y más corto.

  let elementos;
  try {
    elementos = await obtenerContenidoPagina(documentoId, paginaActual);
  } catch (error) {
    contenedorPagina.textContent = "";
    const aviso = document.createElement("p");
    aviso.className = "panel__aviso";
    aviso.textContent = error.mensaje;
    contenedorPagina.appendChild(aviso);
    anunciar(
      "No se ha podido cargar el contenido de la página. " + error.mensaje,
      "assertive"
    );
    return;
  }

  pintarContenido(elementos);

  if (ocrAutomatico) {
    // Fire-and-forget: no se espera aquí (await) para no retrasar el
    // resto de cargarPagina ni el anuncio de "página cargada" que ya
    // emite pintarContenido; las regiones se van actualizando solas
    // según llegan las traducciones.
    procesarFormulasPendientesPagina();
  }
}

function pintarContenido(elementos) {
  contenedorPagina.textContent = "";
  formulasPagina = [];

  if (elementos.length === 0) {
    const vacio = document.createElement("p");
    vacio.className = "pagina__vacia";
    vacio.textContent = "Esta página no contiene texto ni fórmulas detectadas.";
    contenedorPagina.appendChild(vacio);
    anunciar("Página " + paginaActual + ": sin contenido detectado.");
    return;
  }

  elementos.forEach((elemento) => {
    if (elemento.tipo === "texto") {
      const parrafo = document.createElement("p");
      parrafo.className = "pagina__texto";
      parrafo.textContent = elemento.texto;
      contenedorPagina.appendChild(parrafo);
      return;
    }

    if (elemento.tipo === "formula" && elemento.formula) {
      const entrada = crearRegion(elemento.formula, formulasPagina.length + 1);
      formulasPagina.push(entrada);
      contenedorPagina.appendChild(entrada.boton);
    }
  });

  const total = documento.num_paginas || 1;
  if (formulasPagina.length === 0) {
    anunciar(
      "Página " + paginaActual + " de " + total + " cargada. No hay fórmulas en esta página."
    );
  } else {
    // Se omite deliberadamente el recordatorio de Tab/Intro: ya está fijo y
    // visible en el <footer>, y repetirlo en cada página solo alarga el
    // mensaje sin añadir información nueva.
    anunciar(
      "Página " +
        paginaActual +
        " de " +
        total +
        " cargada. " +
        formulasPagina.length +
        (formulasPagina.length === 1 ? " fórmula detectada." : " fórmulas detectadas.")
    );
  }
}


/* Procesar todas */
async function procesarFormulasPendientesPagina() {
  if (procesandoLote) {
    return;
  }

  // Se capturan por referencia el array y el número de página de ESTE
  // momento: si el usuario navega a otra página mientras el lote sigue
  // en curso, pintarContenido ya habrá creado un array nuevo para
  // formulasPagina, y esta comparación por referencia (===) es lo que
  // permite detectarlo más abajo para ignorar eventos que lleguen
  // tarde, en vez de actualizar regiones que ya no están en pantalla.
  const entradasDeEstaPagina = formulasPagina;
  const pendientes = entradasDeEstaPagina.filter((entrada) => !entrada.formula.mathml);
  if (pendientes.length === 0) {
    return;
  }

  procesandoLote = true;
  let errores = 0;

  try {
    await procesarFormulasPagina(documentoId, paginaActual, (evento) => {
      if (formulasPagina !== entradasDeEstaPagina) {
        return;
      }

      if (evento.tipo === "progreso" && evento.formula) {
        const entrada = entradasDeEstaPagina.find(
          (e) => e.formula.id === evento.formula.id
        );
        if (!entrada) {
          return;
        }
        entrada.formula = evento.formula;
        refrescarRegion(entrada, seleccionada === entrada.numero);
        if (seleccionada === entrada.numero) {
          volcarFormulaEnPanel(entrada.formula);
        }
      } else if (evento.tipo === "error_formula") {
        errores += 1;
      }
    });
  } catch (error) {
    procesandoLote = false;
    if (formulasPagina === entradasDeEstaPagina) {
      anunciar(
        "No se ha podido procesar todas las fórmulas de esta página. " + error.mensaje,
        "assertive"
      );
    }
    return;
  }

  procesandoLote = false;
  if (formulasPagina !== entradasDeEstaPagina) {
    return;
  }

  const completadas = pendientes.length - errores;
  if (errores === 0) {
    anunciar("Procesar todas: " + completadas + " fórmulas traducidas.");
  } else {
    anunciar(
      "Procesar todas: " +
        completadas +
        " fórmulas traducidas, " +
        errores +
        (errores === 1 ? " no se ha podido traducir." : " no se han podido traducir."),
      "assertive"
    );
  }
}
function mostrarCargandoPanel(cargando) {
  panelCargando.hidden = !cargando;
  panelContenido.hidden = cargando;
}

function mostrarAvisoPanel(mensaje) {
  if (mensaje) {
    panelAviso.textContent = mensaje;
    panelAviso.hidden = false;
  } else {
    panelAviso.textContent = "";
    panelAviso.hidden = true;
  }
}

function volcarFormulaEnPanel(formula) {
  const valido = pintarMathml(panelVistaPrevia, formula.mathml);
  editorMathml.value = formula.mathml || "";
  mostrarCargandoPanel(false);
  if (!valido && formula.mathml) {
    mostrarAvisoPanel(
      "El MathML almacenado no se ha podido representar. Se muestra su código en la vista previa."
    );
  }
}

async function seleccionarFormula(numero) {
  const entrada = formulasPagina[numero - 1];
  if (!entrada) {
    return;
  }

  if (seleccionada !== null && seleccionada !== numero) {
    const previa = formulasPagina[seleccionada - 1];
    if (previa) {
      refrescarRegion(previa, false);
    }
  }

  seleccionada = numero;
  refrescarRegion(entrada, true);

  panel.hidden = false;
  panelTitulo.textContent = "Fórmula " + numero;
  panelMeta.textContent =
    "Página " +
    entrada.formula.pagina +
    " · Confianza detección YOLO: " +
    Math.round((entrada.formula.confidence_score || 0) * 100) +
    " %";
  mostrarAvisoPanel("");

  panel.focus();

  if (entrada.formula.mathml) {
    volcarFormulaEnPanel(entrada.formula);
    anunciar("Fórmula " + numero + ", ya traducida.");
    return;
  }

  mostrarCargandoPanel(true);
  anunciar("Traduciendo la fórmula " + numero + ". Esto puede tardar unos segundos.");

  let actualizada;
  try {
    actualizada = await consultarFormula(entrada.formula.id);
  } catch (error) {
    if (seleccionada !== numero) {
      return;
    }
    mostrarCargandoPanel(false);
    mostrarAvisoPanel(error.mensaje);
    editorMathml.value = "";
    panelVistaPrevia.textContent = "";
    anunciar(
      "No se ha podido traducir la fórmula " +
        numero +
        ". " +
        error.mensaje +
        " Puedes escribir el MathML a mano en el área de edición.",
      "assertive"
    );
    return;
  }

  if (seleccionada !== numero) {
    entrada.formula = actualizada;
    refrescarRegion(entrada, false);
    return;
  }

  entrada.formula = actualizada;
  volcarFormulaEnPanel(actualizada);
  refrescarRegion(entrada, true);
  anunciar("Fórmula " + numero + " traducida.");
}

function cerrarPanel() {
  if (seleccionada === null) {
    return;
  }
  const entrada = formulasPagina[seleccionada - 1];
  panel.hidden = true;
  mostrarAvisoPanel("");
  seleccionada = null;

  if (entrada) {
    refrescarRegion(entrada, false);
    entrada.boton.focus();
  }
  anunciar("Panel cerrado.");
}

async function guardarCambios() {
  if (seleccionada === null) {
    return;
  }
  const entrada = formulasPagina[seleccionada - 1];
  if (!entrada) {
    return;
  }

  const numero = entrada.numero;
  const mathmlEditado = editorMathml.value;

  btnGuardar.disabled = true;
  mostrarAvisoPanel("");
  anunciar("Guardando los cambios de la fórmula " + numero + ".");

  try {
    const actualizada = await guardarFormula(entrada.formula.id, mathmlEditado);
    entrada.formula = actualizada;

    pintarMathml(panelVistaPrevia, actualizada.mathml);
    refrescarRegion(entrada, true);
    anunciar("Fórmula guardada correctamente.");
  } catch (error) {
    mostrarAvisoPanel(error.mensaje);
    anunciar(
      "No se ha podido guardar la fórmula. " +
        error.mensaje +
        " Revisa la sintaxis del MathML e inténtalo de nuevo.",
      "assertive"
    );
  } finally {
    btnGuardar.disabled = false;
  }
}


/* Eventos */
if (btnCerrarPanel && btnGuardar) {
  btnCerrarPanel.addEventListener("click", cerrarPanel);
  btnGuardar.addEventListener("click", guardarCambios);
}

document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape" && panel && !panel.hidden) {
    evento.preventDefault();
    cerrarPanel();
  }
});

function irAPagina(numero) {
  window.location.href =
    "viewer.xhtml?documento_id=" +
    encodeURIComponent(documentoId) +
    "&pagina=" +
    encodeURIComponent(numero);
}

if (btnAnterior && btnSiguiente && btnCerrarDocumento) {
  btnAnterior.addEventListener("click", () => {
    if (paginaActual > 1) {
      irAPagina(paginaActual - 1);
    }
  });

  btnSiguiente.addEventListener("click", () => {
    if (documento && paginaActual < documento.num_paginas) {
      irAPagina(paginaActual + 1);
    }
  });

  btnCerrarDocumento.addEventListener("click", () => {
    window.location.href = "index.xhtml";
  });
}

function actualizarBotonOcrAutomatico() {
  btnOcrAutomatico.textContent = "Procesar todas las fórmulas: " + (ocrAutomatico ? "Activado" : "Desactivado");
  btnOcrAutomatico.disabled = ocrAutomatico;
}

if (btnOcrAutomatico) {
  btnOcrAutomatico.addEventListener("click", () => {
    // Botón de una sola dirección: activa y se deshabilita. No hay
    // vuelta atrás porque no tendría sentido "desprocesar" las
    // fórmulas ya traducidas de las páginas ya visitadas.
    if (ocrAutomatico) {
      return;
    }
    ocrAutomatico = true;
    actualizarBotonOcrAutomatico();
    anunciar("Procesando las fórmulas pendientes de esta página.");
    procesarFormulasPendientesPagina();
  });
}


/* Arranque */
actualizarBotonOcrAutomatico();
inicializarAnuncios();

cargarDocumento();