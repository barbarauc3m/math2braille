from models.documento import Documento


def _nuevo_documento(nombre="a.pdf", ruta="/tmp/a.pdf", paginas=2):
    return Documento(nombre_archivo=nombre, ruta_archivo=ruta, num_paginas=paginas)


def test_crear_asigna_id_y_fechas(documento_repository):
    creado = documento_repository.crear(_nuevo_documento())
    assert creado.id is not None
    assert creado.fecha_carga is not None
    assert creado.fecha_ultima_apertura is not None
    assert creado.nombre_archivo == "a.pdf"


def test_obtener_por_id_existente(documento_repository):
    creado = documento_repository.crear(_nuevo_documento())
    encontrado = documento_repository.obtener_por_id(creado.id)
    assert encontrado.id == creado.id
    assert encontrado.nombre_archivo == creado.nombre_archivo


def test_obtener_por_id_inexistente(documento_repository):
    assert documento_repository.obtener_por_id(9999) is None


def test_listar_historial_ordena_por_fecha_ultima_apertura_desc(documento_repository, fresh_db):
    from db.connection import db_session

    doc1 = documento_repository.crear(_nuevo_documento(nombre="uno.pdf"))
    doc2 = documento_repository.crear(_nuevo_documento(nombre="dos.pdf"))

    # Fijamos timestamps explícitos y distintos para evitar dependencias
    # de la resolución (segundos) de CURRENT_TIMESTAMP en el test.
    with db_session() as conn:
        conn.execute(
            "UPDATE documento SET fecha_ultima_apertura = ? WHERE id = ?",
            ("2024-01-01 00:00:00", doc2.id),
        )
        conn.execute(
            "UPDATE documento SET fecha_ultima_apertura = ? WHERE id = ?",
            ("2024-06-01 00:00:00", doc1.id),
        )

    historial = documento_repository.listar_historial()
    assert [d.nombre_archivo for d in historial] == ["uno.pdf", "dos.pdf"]


def test_actualizar_fecha_apertura(documento_repository):
    creado = documento_repository.crear(_nuevo_documento())
    fecha_original = creado.fecha_ultima_apertura

    documento_repository.actualizar_fecha_apertura(creado.id)

    actualizado = documento_repository.obtener_por_id(creado.id)
    assert actualizado.fecha_ultima_apertura is not None
    assert fecha_original is not None


def test_eliminar_borra_el_documento(documento_repository):
    creado = documento_repository.crear(_nuevo_documento())
    documento_repository.eliminar(creado.id)
    assert documento_repository.obtener_por_id(creado.id) is None


def test_eliminar_hace_cascade_sobre_formulas(documento_repository, formula_repository):
    from models.formula import Formula

    creado = documento_repository.crear(_nuevo_documento())
    formula_repository.guardar_lote(
        creado.id,
        [Formula(documento_id=creado.id, pagina=1, x=0, y=0, ancho=1, alto=1, confidence_score=0.9)],
    )

    documento_repository.eliminar(creado.id)

    assert formula_repository.obtener_por_documento(creado.id) == []
