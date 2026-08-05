"""
Quota route tests.

PR12: QuotaCheck now has `partition` (default "cpu") and `roles` (default
[]) fields -- previously missing entirely, worked around by mocking
QuotaService.evaluate at the route module level so tests never hit the
real (broken: request.partition didn't exist, and roles was hardcoded to
["gpu_user"] for every caller) path. Still mocked here since these tests
are about the route's DB-wiring/response-shaping, not QuotaService's own
logic (covered by test_quota_service.py) -- but see
test_quota_check_passes_caller_roles_not_hardcoded below for the
regression test locking in the hardcoded-roles fix.
"""
import pytest
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.deps import get_db
from app.models.decision import Decision


def _allow(**kwargs):
    defaults = dict(allow=True, reason="quota ok", remaining_cpu_hours=100.0, remaining_gpu_hours=20.0)
    defaults.update(kwargs)
    return Decision(**defaults)


def _deny(reason="cpu quota exceeded"):
    return Decision(allow=False, reason=reason, remaining_cpu_hours=2.0, remaining_gpu_hours=20.0)


@pytest.fixture
def quota_app():
    from app.api.routes_quota import router
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(quota_app):
    mock_db = MagicMock()
    quota_app.dependency_overrides[get_db] = lambda: mock_db
    return TestClient(quota_app), mock_db


# ---------------------------------------------------------------------------
# POST /quota/check — happy path
# ---------------------------------------------------------------------------

def test_quota_check_allow_within_limits(client):
    tc, mock_db = client
    usage = MagicMock(cpu_hours=10.0, gpu_hours=2.0, jobs_running=0)

    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage), \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=_allow()):

        response = tc.post("/quota/check", json={
            "user_id": "u1",
            "cpu_hours": 5.0,
            "gpu_hours": 1.0,
            "gpus": 1,
        })

    assert response.status_code == 200
    assert response.json()["allow"] is True


def test_quota_check_deny_cpu_exceeded(client):
    tc, mock_db = client
    usage = MagicMock(cpu_hours=118.0, gpu_hours=0.0)

    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage), \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=_deny("cpu quota exceeded")):

        response = tc.post("/quota/check", json={
            "user_id": "u2",
            "cpu_hours": 10.0,
            "gpu_hours": 0.0,
            "gpus": 0,
        })

    assert response.status_code == 200
    data = response.json()
    assert data["allow"] is False
    assert "cpu" in data["reason"].lower()


def test_quota_check_deny_gpu_exceeded(client):
    tc, mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=23.0)

    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage), \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=_deny("gpu quota exceeded")):

        response = tc.post("/quota/check", json={
            "user_id": "u3",
            "cpu_hours": 0.0,
            "gpu_hours": 5.0,
            "gpus": 1,
        })

    assert response.status_code == 200
    assert response.json()["allow"] is False
    assert "gpu" in response.json()["reason"].lower()


def test_quota_check_returns_remaining_hours(client):
    tc, mock_db = client
    usage = MagicMock(cpu_hours=20.0, gpu_hours=4.0)

    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage), \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=_allow(remaining_cpu_hours=90.0, remaining_gpu_hours=18.0)):

        response = tc.post("/quota/check", json={
            "user_id": "u4",
            "cpu_hours": 10.0,
            "gpu_hours": 0.0,
            "gpus": 0,
        })

    data = response.json()
    assert data["allow"] is True
    assert data["remaining_cpu_hours"] == 90.0


def test_quota_check_new_user_creation(client):
    tc, mock_db = client
    new_usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)

    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=new_usage) as mock_service, \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=_allow()):

        response = tc.post("/quota/check", json={
            "user_id": "brand-new",
            "cpu_hours": 1.0,
            "gpu_hours": 0.0,
            "gpus": 0,
        })

    assert response.status_code == 200
    mock_service.assert_called_once_with(mock_db, "brand-new")


def test_quota_check_passes_db_to_usage_service(client):
    tc, mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)

    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage) as mock_service, \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=_allow()):

        tc.post("/quota/check", json={"user_id": "u5", "cpu_hours": 1.0, "gpu_hours": 0.0, "gpus": 0})

    # Verifies DB dependency injection works
    first_arg = mock_service.call_args[0][0]
    assert first_arg is mock_db


def test_quota_check_passes_caller_roles_not_hardcoded(client):
    """Regression test: routes_quota.py used to hardcode roles=["gpu_user"]
    for every request, regardless of the caller's real roles -- meaning
    any user could pass a GPU/DGX quota check. The route must now forward
    whatever roles the caller actually supplied."""
    tc, mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)

    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage), \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=_allow()) as mock_evaluate:

        tc.post("/quota/check", json={
            "user_id": "u6", "cpu_hours": 1.0, "gpu_hours": 0.0, "gpus": 0,
            "roles": ["viewer"],
        })

    assert mock_evaluate.call_args.kwargs["roles"] == ["viewer"]


def test_quota_check_defaults_to_no_roles_when_unsupplied(client):
    tc, mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)

    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage), \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=_allow()) as mock_evaluate:

        tc.post("/quota/check", json={"user_id": "u7", "cpu_hours": 1.0, "gpu_hours": 0.0, "gpus": 0})

    assert mock_evaluate.call_args.kwargs["roles"] == []
