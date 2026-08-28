from fastapi.testclient import TestClient


def test_health():
    import main

    client = TestClient(main.app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_routers_incluidos():
    import main

    client = TestClient(main.app)
    esquema = client.get("/openapi.json").json()
    rutas = set(esquema["paths"].keys())

    assert "/documentos" in rutas
    assert "/formulas/{formula_id}" in rutas


def test_cors_middleware_configurado():
    import main

    nombres_middleware = [m.cls.__name__ for m in main.app.user_middleware]
    assert "CORSMiddleware" in nombres_middleware
