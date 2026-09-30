"""Shared pytest fixtures for the HPC policy engine tests: a mocked database
session and usage record, a client for the policy router, and a client for the
quota router whose database dependency is overridden, so no test connects to
MySQL. It also stubs swagger_ui_bundle when that package is not installed.

Developer: Manish Kumar <manish@omnibioai.org>
"""
import pathlib
import sys
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    import swagger_ui_bundle  # noqa: F401 — load real module so app.main can read its static files
except ImportError:
    _mock_ui_dir = tempfile.mkdtemp()
    pathlib.Path(_mock_ui_dir, "swagger-ui-bundle.js").write_text("/* mock */")
    pathlib.Path(_mock_ui_dir, "swagger-ui.css").write_text("/* mock */")
    _mock_swagger = MagicMock()
    _mock_swagger.swagger_ui_path = _mock_ui_dir
    sys.modules["swagger_ui_bundle"] = _mock_swagger


@pytest.fixture
def mock_db():
    """Provide a MagicMock standing in for a SQLAlchemy session."""
    return MagicMock()


@pytest.fixture
def mock_usage_record():
    """Provide a mock usage record for user "u1" with zero CPU hours, zero GPU hours and no running
    jobs.
    """
    record = MagicMock()
    record.user_id = "u1"
    record.cpu_hours = 0.0
    record.gpu_hours = 0.0
    record.jobs_running = 0
    return record


@pytest.fixture
def policy_client():
    """Provide a TestClient for a FastAPI app that includes only the policy router."""
    from app.api.routes_policy import router
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def quota_client(mock_db):
    """TestClient for quota routes with DB dependency overridden."""
    with patch("app.db.session.create_engine"), \
         patch("app.db.session.SessionLocal"):
        from app.api.deps import get_db
        from app.api.routes_quota import router

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_db] = lambda: mock_db
        yield TestClient(app), mock_db
