from models.documento import Documento
from models.formula import Formula


def _crear_documento(documento_repository):
    return documento_repository.crear(
        Documento(nombre_archivo="a.pdf", ruta_archivo="/tmp/a.pdf", num_paginas=2)
    )


def test_guardar_lote_asigna_ids_y_persiste(documento_repository, formula_repository):
    documento = _crear_documento(documento_repository)
    formulas = [
        Formula(documento_id=documento.id, pagina=1, x=1, y=2, ancho=3, alto=4, confidence_score=0.9),
        Formula(documento_id=documento.id, pagina=1, x=5, y=6, ancho=7, alto=8, confidence_score=0.8),
    ]

    guardadas = formula_repository.guardar_lote(documento.id, formulas)

    assert len(guardadas) == 2
    assert all(f.id is not None for f in guardadas)
    assert all(f.mathml is None for f in guardadas)


def test_guardar_lote_vacio(documento_repository, formula_repository):
    documento = _crear_documento(documento_repository)
    assert formula_repository.guardar_lote(documento.id, []) == []


def test_obtener_por_id_existente(documento_repository, formula_repository):
    documento = _crear_documento(documento_repository)
    [guardada] = formula_repository.guardar_lote(
        documento.id,
        [Formula(documento_id=documento.id, pagina=1, x=0, y=0, ancho=1, alto=1, confidence_score=0.5)],
    )

    encontrada = formula_repository.obtener_por_id(guardada.id)
    assert encontrada.id == guardada.id


def test_obtener_por_id_inexistente(formula_repository):
    assert formula_repository.obtener_por_id(9999) is None


def test_obtener_por_documento_ordena_por_pagina_e_id(documento_repository, formula_repository):
    documento = _crear_documento(documento_repository)
    formula_repository.guardar_lote(
        documento.id,
        [
            Formula(documento_id=documento.id, pagina=2, x=0, y=0, ancho=1, alto=1, confidence_score=0.5),
            Formula(documento_id=documento.id, pagina=1, x=0, y=0, ancho=1, alto=1, confidence_score=0.5),
        ],
    )

    formulas = formula_repository.obtener_por_documento(documento.id)
    assert [f.pagina for f in formulas] == [1, 2]


def test_actualizar_mathml(documento_repository, formula_repository):
    documento = _crear_documento(documento_repository)
    [guardada] = formula_repository.guardar_lote(
        documento.id,
        [Formula(documento_id=documento.id, pagina=1, x=0, y=0, ancho=1, alto=1, confidence_score=0.5)],
    )
    assert guardada.fecha_procesado is None

    actualizada = formula_repository.actualizar_mathml(guardada.id, "<math><mi>x</mi></math>")

    assert actualizada.mathml == "<math><mi>x</mi></math>"
    assert actualizada.fecha_procesado is not None


def test_actualizar_mathml_inexistente(formula_repository):
    assert formula_repository.actualizar_mathml(9999, "<math/>") is None
