import os
from services.documento_service import load_documento_service
from services.formula_service import load_formula_service

os.environ["DATABASE_PATH"] = "./data/db/math2pix_test.sqlite"
os.environ["UPLOADS_PATH"] = "./data/uploads_test"

documento_service = load_documento_service()
formula_service = load_formula_service()

# CU-01: carga completa con progreso
def mostrar_progreso(pagina, total):
    print(f"Detección: página {pagina}/{total}")

with open("../../derivadasyprimitivasprint.pdf", "rb") as f:
    documento = documento_service.cargar_documento(f.read(), "apuntes.pdf", on_progreso=mostrar_progreso)

print("Documento creado:", documento)
print("Nº de páginas:", documento.num_paginas)

# Fórmulas detectadas para ese documento, aún sin mathml
from repositories.formula_repository import FormulaRepository
formulas = FormulaRepository().obtener_por_documento(documento.id)
print(f"{len(formulas)} fórmulas detectadas, procesadas: {sum(f.ya_procesada for f in formulas)}")

# CU-03: consultar la primera fórmula (dispara OCR + conversión + validación)
if formulas:
    formula_procesada = formula_service.consultar_formula(formulas[0].id)
    print("MathML:", formula_procesada.mathml)

    # Segunda llamada: debe devolver el mismo resultado SIN volver a llamar a OCR
    # (compruébalo viendo que no aparece ninguna petición nueva en los logs de service/ocr)
    formula_cacheada = formula_service.consultar_formula(formulas[0].id)
    assert formula_cacheada.mathml == formula_procesada.mathml
    print("Caché de CU-03 funcionando correctamente")

    # CU-04: editar con un MathML válido
    formula_editada = formula_service.editar_formula(
        formulas[0].id, "<math><mi>x</mi><mo>+</mo><mn>1</mn></math>"
    )
    print("MathML tras edición:", formula_editada.mathml)

    # CU-04: intentar editar con algo inválido — debe lanzar XhtmlValidationError
    # y el mathml de arriba debe seguir intacto (RF-11)
    from utils.xhtml_validator import XhtmlValidationError
    try:
        formula_service.editar_formula(formulas[0].id, "<div>no es math</div>")
        print("ERROR: debería haber lanzado XhtmlValidationError")
    except XhtmlValidationError:
        print("Rechazo de edición inválida: OK")

# RF-15/CU-06: reabrir sin re-ejecutar YOLO
documento_service.abrir_documento(documento.id)

# RF-14/CU-05: historial
print("Historial:", documento_service.listar_historial())

# RF-16/CU-07: eliminar y comprobar cascada
documento_service.eliminar_documento(documento.id)
assert FormulaRepository().obtener_por_documento(documento.id) == []
print("Eliminación en cascada: OK")