"""
Tests for app/main.py and app/api/deps.py.
app/main.py calls Base.metadata.create_all at import time — we patch it before
importing so no MySQL connection is needed.

Developer: Manish Kumar <manish@omnibioai.org>
"""
import sys
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def hpc_app():
    """Import app.main with create_all patched."""
    sys.modules.pop("app.main", None)

    from app.db.session import Base
    with patch.object(Base.metadata, "create_all"):
        import app.main as main_mod
        yield main_mod.app


def _route_paths(routes):
    paths = []
    for route in routes:
        path = getattr(route, "path", None)
        if path is not None:
            paths.append(path)
        nested = getattr(route, "routes", None)
        if nested is None:
            nested = getattr(getattr(route, "original_router", None), "routes", None)
        if nested:
            paths.extend(_route_paths(nested))
    return paths


# ---------------------------------------------------------------------------
# GET /  (root)
# ---------------------------------------------------------------------------

def test_root_returns_service_info(hpc_app):
    """GET / returns 200 with the service name "omnibioai-hpc-policy-engine" and status "running".
    """
    client = TestClient(hpc_app)
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["service"] == "omnibioai-hpc-policy-engine"
    assert data["status"] == "running"


def test_app_includes_jobs_router(hpc_app):
    """The app registers a job evaluation route."""
    paths = _route_paths(hpc_app.routes)
    assert any("evaluate" in p for p in paths)


def test_app_includes_quota_router(hpc_app):
    """The app registers a quota route."""
    paths = _route_paths(hpc_app.routes)
    assert any("quota" in p for p in paths)


# ---------------------------------------------------------------------------
# app/api/deps.py — get_db generator
# ---------------------------------------------------------------------------

def test_get_db_yields_session():
    """get_db yields the session created by SessionLocal."""
    mock_session = MagicMock()
    with patch("app.api.deps.SessionLocal", return_value=mock_session):
        from app.api.deps import get_db
        gen = get_db()
        db = next(gen)
        assert db is mock_session


def test_get_db_closes_session_on_exit():
    """get_db closes the session once after its consumer finishes."""
    mock_session = MagicMock()
    with patch("app.api.deps.SessionLocal", return_value=mock_session):
        from app.api.deps import get_db
        gen = get_db()
        next(gen)
        try:
            next(gen)
        except StopIteration:
            pass
    mock_session.close.assert_called_once()


def test_get_db_closes_session_on_exception():
    """get_db still closes the session once when its consumer raises."""
    mock_session = MagicMock()
    with patch("app.api.deps.SessionLocal", return_value=mock_session):
        from app.api.deps import get_db
        gen = get_db()
        next(gen)
        with pytest.raises(Exception, match="something broke"):
            gen.throw(Exception("something broke"))
    mock_session.close.assert_called_once()
