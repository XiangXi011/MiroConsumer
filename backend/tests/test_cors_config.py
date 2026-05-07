"""Tests for Flask CORS configuration."""

from app import create_app
from app.config import Config


def test_cors_uses_comma_split_origins(monkeypatch):
    """CORS must split CORS_ALLOWED_ORIGINS by comma instead of using wildcard."""
    monkeypatch.setattr(Config, "CORS_ALLOWED_ORIGINS", "http://localhost:3000,https://example.com")
    app = create_app(config_class=Config)

    @app.route("/api/cors-probe")
    def cors_probe():
        return {"ok": True}

    with app.test_client() as client:
        allowed = client.get("/api/cors-probe", headers={"Origin": "https://example.com"})
        blocked = client.get("/api/cors-probe", headers={"Origin": "https://evil.example"})

    assert allowed.headers["Access-Control-Allow-Origin"] == "https://example.com"
    assert "Access-Control-Allow-Origin" not in blocked.headers
