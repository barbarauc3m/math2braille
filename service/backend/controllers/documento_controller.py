"""
Endpoint de subida (POST /documentos) que transmite el progreso de la detección adelantada mediante streaming NDJSON: cada
línea es un objeto JSON independiente, sin necesidad de websockets.
DocumentoService.cargar_documento ya acepta un callback on_progreso; aquí se ejecuta en un hilo aparte y se traduce cada llamada al callback en una línea que se va enviando al cliente según ocurre.
"""

import json
import queue
import threading

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from api_schemas import ContenidoPaginaOut, DocumentoOut, ElementoFormulaOut, ElementoTextoOut, FormulasDocumentoOut, FormulaOut, HistorialOut


from api_schemas import DocumentoOut, FormulasDocumentoOut, FormulaOut, HistorialOut
from dependencies import get_documento_service, get_formula_service
from services.documento_service import DocumentoService
from services.formula_service import FormulaService
from services.exceptions import DocumentoNoEncontradoError

router = APIRouter(prefix="/documentos", tags=["documentos"])


def _documento_a_schema(documento) -> DocumentoOut:
    return DocumentoOut(
        id=documento.id,
        nombre_archivo=documento.nombre_archivo,
        num_paginas=documento.num_paginas,
        fecha_carga=documento.fecha_carga,
        fecha_ultima_apertura=documento.fecha_ultima_apertura,
    )


def _formula_a_schema(formula) -> FormulaOut:
    return FormulaOut(
        id=formula.id, pagina=formula.pagina, x=formula.x, y=formula.y,
        ancho=formula.ancho, alto=formula.alto,
        confidence_score=formula.confidence_score,
        mathml=formula.mathml, fecha_procesado=formula.fecha_procesado,
    )


@router.post("")
async def subir_documento(
    file: UploadFile = File(...),
    documento_service: DocumentoService = Depends(get_documento_service),
):
    """
    Sube un PDF y lanza la detección adelantada de todas
    sus páginas. Devuelve un stream NDJSON: una línea por página
    procesada ({"tipo": "progreso", ...}), y una línea final con el
    documento creado ({"tipo": "completado", ...}) o un error
    ({"tipo": "error", ...}).
    """
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="El fichero debe ser un PDF")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Fichero PDF vacío")

    eventos: "queue.Queue" = queue.Queue()
    resultado: dict = {}

    def procesar():
        def on_progreso(pagina: int, total: int):
            eventos.put({"tipo": "progreso", "pagina": pagina, "total": total})

        try:
            documento = documento_service.cargar_documento(
                pdf_bytes, file.filename, on_progreso=on_progreso
            )
            resultado["documento"] = documento
        except Exception as e:
            resultado["error"] = str(e)
        finally:
            eventos.put(None)  # señal de fin de stream

    hilo = threading.Thread(target=procesar, daemon=True)
    hilo.start()

    def event_stream():
        while True:
            evento = eventos.get()
            if evento is None:
                break
            yield json.dumps(evento) + "\n"

        hilo.join()
        if "error" in resultado:
            yield json.dumps({"tipo": "error", "detalle": resultado["error"]}) + "\n"
        else:
            doc_schema = _documento_a_schema(resultado["documento"])
            yield json.dumps({"tipo": "completado", "documento": doc_schema.model_dump()}) + "\n"

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")


@router.get("", response_model=HistorialOut)
def listar_historial(documento_service: DocumentoService = Depends(get_documento_service)):
    """RF-14/CU-05."""
    documentos = documento_service.listar_historial()
    return HistorialOut(documentos=[_documento_a_schema(d) for d in documentos])


@router.get("/{documento_id}", response_model=DocumentoOut)
def abrir_documento(
    documento_id: int,
    documento_service: DocumentoService = Depends(get_documento_service),
):
    """
    RF-15/CU-06: reabre un documento del historial sin re-ejecutar YOLO.
    """
    try:
        documento = documento_service.abrir_documento(documento_id)
    except DocumentoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return _documento_a_schema(documento)


@router.get("/{documento_id}/formulas", response_model=FormulasDocumentoOut)
def obtener_formulas(
    documento_id: int,
    formula_service: FormulaService = Depends(get_formula_service),
):
    """RF-07: fórmulas de un documento para pintar las regiones del visor."""
    formulas = formula_service.obtener_formulas_documento(documento_id)
    return FormulasDocumentoOut(formulas=[_formula_a_schema(f) for f in formulas])


@router.delete("/{documento_id}", status_code=204)
def eliminar_documento(
    documento_id: int,
    documento_service: DocumentoService = Depends(get_documento_service),
):
    """El cascade de schema.sql elimina las fórmulas asociadas."""
    try:
        documento_service.eliminar_documento(documento_id)
    except DocumentoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))
    
@router.get("/{documento_id}/paginas/{numero_pagina}/contenido", response_model=ContenidoPaginaOut)
def obtener_contenido_pagina(
    documento_id: int,
    numero_pagina: int,
    documento_service: DocumentoService = Depends(get_documento_service),
):
    """Leer contenido completo de una página (texto + fórmulas)."""
    try:
        elementos = documento_service.obtener_contenido_pagina(documento_id, numero_pagina)
    except DocumentoNoEncontradoError as e:
        raise HTTPException(status_code=404, detail=str(e))

    elementos_out = []
    for e in elementos:
        if e["tipo"] == "texto":
            elementos_out.append(ElementoTextoOut(texto=e["texto"]))
        else:
            elementos_out.append(ElementoFormulaOut(formula=_formula_a_schema(e["formula"])))

    return ContenidoPaginaOut(elementos=elementos_out)