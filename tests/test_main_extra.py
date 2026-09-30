"""
Cover app/main.py endpoints not reached by test_main.py:
  - GET /health          → line 79
  - GET /docs            → lines 46-70
  - GET /swagger-static/ → lines 38-41

Developer: Manish Kumar <manish@omnibioai.org>
"""
import sys
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def main_client():
    """Provide a TestClient for app.main with the database table creation patched out."""
    sys.modules.pop("app.main", None)
    from app.db.session import Base
    with patch.object(Base.metadata, "create_all"):
        import app.main as _mod
        yield TestClient(_mod.app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------

def test_health_returns_ok(main_client):
    """GET /health returns 200 with {"status": "ok"}."""
    response = main_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


# ---------------------------------------------------------------------------
# GET /docs  (custom Swagger UI)
# ---------------------------------------------------------------------------

def test_docs_returns_html(main_client):
    """GET /docs returns 200 with an HTML content type."""
    response = main_client.get("/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_docs_contains_swagger_ui_bundle(main_client):
    """The /docs page references swagger-ui."""
    response = main_client.get("/docs")
    assert "swagger-ui" in response.text.lower()


def test_docs_contains_spec_json(main_client):
    """The /docs page includes the SwaggerUIBundle initialization."""
    response = main_client.get("/docs")
    assert "SwaggerUIBundle" in response.text


# ---------------------------------------------------------------------------
# GET /swagger-static/{path}
# ---------------------------------------------------------------------------

def test_swagger_static_missing_file_returns_404(main_client):
    """Requesting a nonexistent file under /swagger-static returns 404."""
    response = main_client.get("/swagger-static/definitely-does-not-exist-xyz123.js")
    assert response.status_code == 404


def test_swagger_static_existing_file_returns_200(main_client):
    """Requesting swagger-ui-bundle.js under /swagger-static returns 200."""
    # swagger-ui-bundle.js is always present (real package or conftest mock)
    response = main_client.get("/swagger-static/swagger-ui-bundle.js")
    assert response.status_code == 200


def test_swagger_static_css_file_returns_200(main_client):
    """Requesting swagger-ui.css under /swagger-static returns 200."""
    response = main_client.get("/swagger-static/swagger-ui.css")
    assert response.status_code == 200
