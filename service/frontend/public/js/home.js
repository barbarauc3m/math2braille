/* Lógica de la pantalla de inicio (index.xhtml).

Esta pantalla permite subir un documento nuevo, reabrir uno del historial, 
consultar el historial y eliminar un documento.*/


/* Referencias al DOM */
const cabecera = document.querySelector(".cabecera");
const principal = document.querySelector("main.inicio");

const btnNuevo = document.getElementById("btn-nuevo");
const btnHistorial = document.getElementById("btn-historial");
const inputPdf = document.getElementById("input-pdf");

const bloqueAcciones = document.getElementById("inicio-acciones");
const bloqueProgreso = document.getElementById("inicio-progreso");
const textoProgreso = document.getElementById("progreso-texto");
const barraProgreso = document.getElementById("progreso-barra");
const rellenoProgreso = document.getElementById("progreso-relleno");

const capaModal = document.getElementById("capa-modal");
const modal = document.getElementById("modal-historial");
const tituloModal = document.getElementById("modal-titulo");
const cuerpoModal = document.getElementById("modal-cuerpo");
const btnCerrarModal = document.getElementById("btn-cerrar-modal");

/* Elemento al que hay que devolver el foco cuando se cierre el modal. */
let focoPrevioAlModal = null;


/* Navegación */
function irAlVisor(documentoId) {
  window.location.href =
    "viewer.xhtml?documento_id=" + encodeURIComponent(documentoId) + "&pagina=1";
}


/* Subida de un documento nuevo */
function mostrarProgreso(visible) {
  bloqueAcciones.hidden = visible;
  bloqueProgreso.hidden = !visible;
  if (visible) {
    actualizarBarra(0, "Subiendo el documento…");
  }
}

function actualizarBarra(porcentaje, texto) {
  const valor = Math.max(0, Math.min(100, Math.round(porcentaje)));
  rellenoProgreso.style.width = valor + "%";
  barraProgreso.setAttribute("aria-valuenow", String(valor));
  barraProgreso.setAttribute("aria-valuetext", texto);
  textoProgreso.textContent = texto;
}

async function procesarSubida(archivo) {
  mostrarProgreso(true);
  anunciar("Subiendo " + archivo.name + ".");

  let documentoCreado = null;

  try {
    await subirDocumento(archivo, (evento) => {
      if (evento.tipo === "progreso") {
        const total = evento.total || 1;
        const mensaje =
          "Detectando fórmulas: página " + evento.pagina + " de " + total + ".";
        actualizarBarra((evento.pagina / total) * 100, mensaje);
        anunciar(mensaje, "polite");
      } else if (evento.tipo === "completado") {
        documentoCreado = evento.documento;
      } else if (evento.tipo === "error") {
        throw new ErrorApi(evento.detalle || "El procesamiento ha fallado.", 500);
      }
    });
  } catch (error) {
    mostrarProgreso(false);
    const detalle = error instanceof ErrorApi ? error.mensaje : "Error inesperado.";
    anunciar(
      "No se ha podido procesar el documento. " +
        detalle +
        ". Comprueba que el fichero es un PDF válido e inténtalo de nuevo.",
      "assertive"
    );
    btnNuevo.focus();
    return;
  }

  if (!documentoCreado) {
    mostrarProgreso(false);
    anunciar(
      "El servidor no ha confirmado la carga del documento. Inténtalo de nuevo.",
      "assertive"
    );
    btnNuevo.focus();
    return;
  }

  actualizarBarra(100, "Documento cargado.");
  anunciar(
    "Documento " +
      documentoCreado.nombre_archivo +
      " cargado con " +
      documentoCreado.num_paginas +
      " páginas. Abriendo el visor."
  );
  irAlVisor(documentoCreado.id);
}

if (btnNuevo && inputPdf) {
  btnNuevo.addEventListener("click", () => {
    inputPdf.click();
  });

  inputPdf.addEventListener("change", () => {
    const archivo = inputPdf.files && inputPdf.files[0];
    inputPdf.value = "";
    if (archivo) {
      procesarSubida(archivo);
    }
  });
}


/* Modal de historial */
const SELECTOR_ENFOCABLES =
  'button:not([disabled]), [href], input:not([disabled]):not([tabindex="-1"]), ' +
  'textarea:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])';

function enfocablesDelModal() {
  return Array.prototype.filter.call(
    modal.querySelectorAll(SELECTOR_ENFOCABLES),
    (el) => el.getClientRects().length > 0
  );
}

function formatearFecha(valor) {
  if (!valor) {
    return "sin registrar";
  }
  const fecha = new Date(String(valor).replace(" ", "T"));
  if (Number.isNaN(fecha.getTime())) {
    return String(valor);
  }
  return new Intl.DateTimeFormat("es-ES", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(fecha);
}

function abrirModal() {
  focoPrevioAlModal = document.activeElement;
  capaModal.hidden = false;
  desactivarFondo(true);

  cuerpoModal.textContent = "";
  const cargando = document.createElement("p");
  cargando.textContent = "Cargando historial…";
  cuerpoModal.appendChild(cargando);

  tituloModal.focus();
  cargarHistorial();
}

function cerrarModal() {
  capaModal.hidden = true;
  desactivarFondo(false);
  if (focoPrevioAlModal && typeof focoPrevioAlModal.focus === "function") {
    focoPrevioAlModal.focus();
  } else {
    btnHistorial.focus();
  }
  focoPrevioAlModal = null;
}

function desactivarFondo(inerte) {
  [cabecera, principal].forEach((el) => {
    if (!el) {
      return;
    }
    el.inert = inerte;
    if (inerte) {
      el.setAttribute("aria-hidden", "true");
    } else {
      el.removeAttribute("aria-hidden");
    }
  });
}

async function cargarHistorial() {
  let documentos;
  try {
    documentos = await listarDocumentos();
  } catch (error) {
    cuerpoModal.textContent = "";
    const aviso = document.createElement("p");
    aviso.className = "panel__aviso";
    aviso.textContent = error.mensaje;
    cuerpoModal.appendChild(aviso);
    anunciar("No se ha podido cargar el historial. " + error.mensaje, "assertive");
    return;
  }
  renderizarHistorial(documentos);
}

function renderizarHistorial(documentos) {
  cuerpoModal.textContent = "";

  if (documentos.length === 0) {
    const vacio = document.createElement("p");
    vacio.textContent = "Aún no has abierto ningún documento.";
    cuerpoModal.appendChild(vacio);
    anunciar("Aún no has abierto ningún documento.");
    return;
  }

  const lista = document.createElement("ul");
  lista.className = "historial";

  documentos.forEach((doc) => {
    lista.appendChild(crearItemHistorial(doc));
  });

  cuerpoModal.appendChild(lista);
  anunciar(
    documentos.length === 1
      ? "Historial cargado: 1 documento."
      : "Historial cargado: " + documentos.length + " documentos."
  );
}

function crearItemHistorial(doc) {
  const item = document.createElement("li");
  item.className = "historial__item";

  const info = document.createElement("div");

  const nombre = document.createElement("p");
  nombre.className = "historial__nombre";
  nombre.textContent = doc.nombre_archivo;

  const meta = document.createElement("p");
  meta.className = "historial__meta";
  meta.textContent =
    doc.num_paginas +
    (doc.num_paginas === 1 ? " página · Última apertura: " : " páginas · Última apertura: ") +
    formatearFecha(doc.fecha_ultima_apertura) + " UTC";

  info.appendChild(nombre);
  info.appendChild(meta);

  const acciones = document.createElement("div");
  acciones.className = "historial__acciones";

  const btnEliminar = document.createElement("button");
  btnEliminar.type = "button";
  btnEliminar.className = "boton boton--peligro";
  btnEliminar.textContent = "Eliminar";
  btnEliminar.setAttribute("aria-label", "Eliminar " + doc.nombre_archivo);
  btnEliminar.addEventListener("click", () => eliminarDelHistorial(doc));

  const btnAbrir = document.createElement("button");
  btnAbrir.type = "button";
  btnAbrir.className = "boton boton--principal";
  btnAbrir.textContent = "Abrir";
  btnAbrir.setAttribute("aria-label", "Abrir " + doc.nombre_archivo);
  btnAbrir.addEventListener("click", () => abrirDelHistorial(doc));

  acciones.appendChild(btnEliminar);
  acciones.appendChild(btnAbrir);

  item.appendChild(info);
  item.appendChild(acciones);
  return item;
}

async function abrirDelHistorial(doc) {
  anunciar("Abriendo " + doc.nombre_archivo + ".");
  try {
    await abrirDocumento(doc.id);
  } catch (error) {
    anunciar(
      "No se ha podido abrir " + doc.nombre_archivo + ". " + error.mensaje,
      "assertive"
    );
    return;
  }
  irAlVisor(doc.id);
}

async function eliminarDelHistorial(doc) {
  const confirmado = window.confirm(
    "¿Seguro que quieres eliminar «" +
      doc.nombre_archivo +
      "» del historial? Se borrarán también las fórmulas ya traducidas de este documento."
  );
  if (!confirmado) {
    anunciar("Eliminación cancelada.");
    return;
  }

  try {
    await eliminarDocumento(doc.id);
  } catch (error) {
    anunciar(
      "No se ha podido eliminar " + doc.nombre_archivo + ". " + error.mensaje,
      "assertive"
    );
    return;
  }

  anunciar(doc.nombre_archivo + " eliminado del historial.");
  tituloModal.focus();
  await cargarHistorial();
}

/* Apertura, cierre y trampa de foco del modal */
if (btnHistorial && btnCerrarModal && capaModal) {
  btnHistorial.addEventListener("click", abrirModal);
  btnCerrarModal.addEventListener("click", cerrarModal);

  capaModal.addEventListener("mousedown", (evento) => {
    if (evento.target === capaModal) {
      cerrarModal();
    }
  });

  capaModal.addEventListener("keydown", (evento) => {
    if (evento.key === "Escape") {
      evento.preventDefault();
      cerrarModal();
      return;
    }

    if (evento.key !== "Tab") {
      return;
    }

    const enfocables = enfocablesDelModal();
    if (enfocables.length === 0) {
      evento.preventDefault();
      return;
    }
    const primero = enfocables[0];
    const ultimo = enfocables[enfocables.length - 1];
    const actual = document.activeElement;

    if (evento.shiftKey && (actual === primero || actual === tituloModal)) {
      evento.preventDefault();
      ultimo.focus();
    } else if (!evento.shiftKey && actual === ultimo) {
      evento.preventDefault();
      primero.focus();
    }
  });
}


/* Arranque */
inicializarAnuncios();
