"""
Direct-source unit tests for app/api/routes_quota.py (POST /quota/check).

Loaded via tests/_srcload.py (see that module's docstring) so its own lines
are measured even where the checked-in .so shadows the .py import. Exercised
through a real FastAPI TestClient with the DB dependency overridden by a
MagicMock (same approach as tests/test_routes_quota.py, kept intact, not
modified) -- no real MySQL connection is used. This file adds
validation/edge-case and identity coverage that file doesn't target.

UsageService.get_or_create_user_usage and QuotaService.evaluate are mocked
at the routes_quota module boundary in most tests here so the route's own
DB-wiring/response-shaping/role-forwarding logic is what's under test (the
underlying QuotaService/quota logic itself is covered by
test_quota_service_source.py and test_core_quota_source.py). A couple of
tests run the real QuotaService end to end to prove the route's roles/
partition forwarding actually reaches policy-critical decisions.
"""
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.models.decision import Decision
from tests._srcload import load

routes_quota_mod = load("app/api/routes_quota.py")


def _allow(**kwargs):
    defaults = {"allow": True, "reason": "quota ok", "remaining_cpu_hours": 100.0, "remaining_gpu_hours": 20.0}
    defaults.update(kwargs)
    return Decision(**defaults)


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(routes_quota_mod.router)
    mock_db = MagicMock()
    app.dependency_overrides[routes_quota_mod.get_db] = lambda: mock_db
    return TestClient(app), mock_db


# ---------------------------------------------------------------------------
# Core happy/deny path (mirrors test_routes_quota.py, source-loaded)
# ---------------------------------------------------------------------------

def test_quota_check_allow(client):
    tc, _mock_db = client
    usage = MagicMock(cpu_hours=10.0, gpu_hours=2.0)
    with patch.object(routes_quota_mod.UsageService, "get_or_create_user_usage", return_value=usage), \
         patch.object(routes_quota_mod.QuotaService, "evaluate", return_value=_allow()):
        response = tc.post("/quota/check", json={"user_id": "u1", "cpu_hours": 1.0})
    assert response.status_code == 200
    assert response.json()["allow"] is True


def test_quota_check_deny(client):
    tc, _mock_db = client
    usage = MagicMock(cpu_hours=119.0, gpu_hours=0.0)
    denied = Decision(allow=False, reason="cpu quota exceeded", remaining_cpu_hours=1.0, remaining_gpu_hours=24.0)
    with patch.object(routes_quota_mod.UsageService, "get_or_create_user_usage", return_value=usage), \
         patch.object(routes_quota_mod.QuotaService, "evaluate", return_value=denied):
        response = tc.post("/quota/check", json={"user_id": "u2", "cpu_hours": 5.0})
    assert response.json()["allow"] is False


def test_roles_forwarded_to_quota_service_not_hardcoded(client):
    tc, _mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)
    with patch.object(routes_quota_mod.UsageService, "get_or_create_user_usage", return_value=usage), \
         patch.object(routes_quota_mod.QuotaService, "evaluate", return_value=_allow()) as mock_eval:
        tc.post("/quota/check", json={"user_id": "u3", "roles": ["viewer"]})
    assert mock_eval.call_args.kwargs["roles"] == ["viewer"]


def test_roles_default_to_empty_list_when_unsupplied(client):
    tc, _mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)
    with patch.object(routes_quota_mod.UsageService, "get_or_create_user_usage", return_value=usage), \
         patch.object(routes_quota_mod.QuotaService, "evaluate", return_value=_allow()) as mock_eval:
        tc.post("/quota/check", json={"user_id": "u4"})
    assert mock_eval.call_args.kwargs["roles"] == []


# ---------------------------------------------------------------------------
# End-to-end (real QuotaService, no mocking of policy logic)
# ---------------------------------------------------------------------------

def test_end_to_end_gpu_request_denied_without_role(client):
    tc, _mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)
    with patch.object(routes_quota_mod.UsageService, "get_or_create_user_usage", return_value=usage):
        response = tc.post("/quota/check", json={"user_id": "u5", "gpus": 2})
    data = response.json()
    assert data["allow"] is False
    assert data["reason"] == "gpu access denied"


def test_end_to_end_dgx_partition_allowed_with_correct_roles(client):
    tc, _mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)
    with patch.object(routes_quota_mod.UsageService, "get_or_create_user_usage", return_value=usage):
        response = tc.post("/quota/check", json={
            "user_id": "u6", "gpus": 1, "gpu_hours": 1.0,
            "partition": "dgx-a100", "roles": ["gpu_user", "dgx_access"],
        })
    assert response.json()["allow"] is True


# ---------------------------------------------------------------------------
# Validation / identity edge cases
# ---------------------------------------------------------------------------

def test_missing_user_id_rejected(client):
    tc, _mock_db = client
    response = tc.post("/quota/check", json={"cpu_hours": 1.0})
    assert response.status_code == 422


def test_malformed_json_body_rejected(client):
    tc, _mock_db = client
    response = tc.post(
        "/quota/check",
        content="{not valid json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422


def test_roles_wrong_type_rejected(client):
    tc, _mock_db = client
    response = tc.post("/quota/check", json={"user_id": "u7", "roles": "gpu_user"})
    assert response.status_code == 422


def test_negative_cpu_hours_accepted_without_validation(client):
    """Characterizes current behavior: cpu_hours has no ge=0 constraint on
    QuotaCheck, so a negative request is accepted at the API boundary."""
    tc, _mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)
    with patch.object(routes_quota_mod.UsageService, "get_or_create_user_usage", return_value=usage):
        response = tc.post("/quota/check", json={"user_id": "u8", "cpu_hours": -10.0})
    assert response.status_code == 200
    assert response.json()["allow"] is True


def test_db_session_from_dependency_override_is_used(client):
    tc, mock_db = client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)
    with patch.object(routes_quota_mod.UsageService, "get_or_create_user_usage", return_value=usage) as mock_svc, \
         patch.object(routes_quota_mod.QuotaService, "evaluate", return_value=_allow()):
        tc.post("/quota/check", json={"user_id": "u9"})
    assert mock_svc.call_args[0][0] is mock_db
