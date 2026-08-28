def test_get_documento_service_es_singleton():
    import dependencies

    assert dependencies.get_documento_service() is dependencies.get_documento_service()


def test_get_formula_service_es_singleton():
    import dependencies

    assert dependencies.get_formula_service() is dependencies.get_formula_service()


def test_get_documento_service_devuelve_documento_service():
    import dependencies
    from services.documento_service import DocumentoService

    assert isinstance(dependencies.get_documento_service(), DocumentoService)


def test_get_formula_service_devuelve_formula_service():
    import dependencies
    from services.formula_service import FormulaService

    assert isinstance(dependencies.get_formula_service(), FormulaService)
