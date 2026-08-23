/**
 * Capa de acceso a la API REST de service/backend.
 *
 * Todo el frontend habla con el backend exclusivamente a través de este
 * módulo: ningún otro fichero llama a fetch() directamente. Así el contrato
 * con la API queda documentado en un solo sitio y los módulos de interfaz
 * (home.js, viewer.js) solo tratan con objetos ya normalizados y con un
 * único tipo de error.
 */

class ErrorApi extends Error {
  constructor(mensaje, estado = 0) {
    super(mensaje);
    this.name = "ErrorApi";
    this.mensaje = mensaje;
    this.estado = estado;
  }
}

function url(ruta) {
  return `${BACKEND_URL}${ruta}`;
}

async function leerDetalleError(respuesta) {
  try {
    const cuerpo = await respuesta.json();
    if (cuerpo && typeof cuerpo.detail === "string") {
      return cuerpo.detail;
    }
    if (cuerpo && Array.isArray(cuerpo.detail) && cuerpo.detail.length > 0) {
      return cuerpo.detail.map((d) => d.msg || "").join(" ");
    }
  } catch (error) {
    /* la respuesta no era JSON */
  }
  return `El servidor ha respondido con el código ${respuesta.status}.`;
}

async function pedirJson(ruta, opciones = {}) {
  let respuesta;
  try {
    respuesta = await fetch(url(ruta), opciones);
  } catch (error) {
    throw new ErrorApi(
      "No se ha podido contactar con el servidor. Comprueba que el backend está en marcha.",
      0
    );
  }
  if (!respuesta.ok) {
    throw new ErrorApi(await leerDetalleError(respuesta), respuesta.status);
  }
  if (respuesta.status === 204) {
    return null;
  }
  return respuesta.json();
}

/* Documentos */

async function subirDocumento(archivo, alRecibirEvento) {
  const datos = new FormData();
  datos.append("file", archivo);

  let respuesta;
  try {
    respuesta = await fetch(url("/documentos"), { method: "POST", body: datos });
  } catch (error) {
    throw new ErrorApi(
      "No se ha podido contactar con el servidor. Comprueba que el backend está en marcha.",
      0
    );
  }

  if (!respuesta.ok) {
    throw new ErrorApi(await leerDetalleError(respuesta), respuesta.status);
  }
  if (!respuesta.body) {
    throw new ErrorApi("El servidor no ha devuelto ningún flujo de progreso.", 0);
  }

  const lector = respuesta.body.getReader();
  const decodificador = new TextDecoder("utf-8");
  let pendiente = "";

  const procesarLinea = (linea) => {
    const limpia = linea.trim();
    if (limpia === "") {
      return;
    }
    let evento;
    try {
      evento = JSON.parse(limpia);
    } catch (error) {
      return;
    }
    alRecibirEvento(evento);
  };

  for (;;) {
    const { value, done } = await lector.read();
    if (done) {
      break;
    }
    pendiente += decodificador.decode(value, { stream: true });
    let corte = pendiente.indexOf("\n");
    while (corte >= 0) {
      procesarLinea(pendiente.slice(0, corte));
      pendiente = pendiente.slice(corte + 1);
      corte = pendiente.indexOf("\n");
    }
  }
  pendiente += decodificador.decode();
  procesarLinea(pendiente);
}

async function listarDocumentos() {
  const datos = await pedirJson("/documentos");
  return datos && Array.isArray(datos.documentos) ? datos.documentos : [];
}

function abrirDocumento(documentoId) {
  return pedirJson(`/documentos/${documentoId}`);
}

function eliminarDocumento(documentoId) {
  return pedirJson(`/documentos/${documentoId}`, { method: "DELETE" });
}

async function obtenerContenidoPagina(documentoId, numeroPagina) {
  const datos = await pedirJson(
    `/documentos/${documentoId}/paginas/${numeroPagina}/contenido`
  );
  return datos && Array.isArray(datos.elementos) ? datos.elementos : [];
}

/* Fórmulas */

function consultarFormula(formulaId) {
  return pedirJson(`/formulas/${formulaId}`);
}

function guardarFormula(formulaId, mathml) {
  return pedirJson(`/formulas/${formulaId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mathml }),
  });
}