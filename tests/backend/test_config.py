import importlib


def test_frontend_origins_default(monkeypatch):
    monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
    import config

    importlib.reload(config)
    try:
        assert config.FRONTEND_ORIGINS == ["http://127.0.0.1", "http://localhost"]
    finally:
        importlib.reload(config)


def test_frontend_origins_from_env(monkeypatch):
    monkeypatch.setenv("FRONTEND_ORIGIN", "http://a.com,http://b.com")
    import config

    importlib.reload(config)
    try:
        assert config.FRONTEND_ORIGINS == ["http://a.com", "http://b.com"]
    finally:
        monkeypatch.delenv("FRONTEND_ORIGIN", raising=False)
        importlib.reload(config)
