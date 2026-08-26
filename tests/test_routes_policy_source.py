"""
Direct-source unit tests for app/api/routes_policy.py (POST /jobs/evaluate).

Loaded via tests/_srcload.py (see that module's docstring) so its own lines
are measured even where the checked-in .so shadows the .py import. Exercised
through a real FastAPI TestClient (not by calling the handler function
directly) so request validation, JSON parsing, and response shaping all run
for real, same as tests/test_routes_policy.py (kept intact, not modified).
This file adds validation/edge-case coverage that file doesn't target:
negative resource values, malformed roles, unknown/extra fields, malformed
JSON bodies, and the org_id no-op characterization.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from tests._srcload import load

routes_policy_mod = load("app/api/routes_policy.py")


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(routes_policy_mod.router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Core allow/deny precedence (mirrors test_routes_policy.py, source-loaded)
# ---------------------------------------------------------------------------

def test_default_request_approved(client):
    response = client.post("/jobs/evaluate", json={"user_id": "u1"})
    assert response.status_code == 200
    assert response.json() == {"allow": True, "reason": "job approved", "partition": "cpu"}


def test_gpu_request_without_role_denied(client):
    response = client.post("/jobs/evaluate", json={"user_id": "u1", "gpus": 2})
    data = response.json()
    assert data["allow"] is False
    assert data["reason"] == "gpu access denied"


def test_dgx_request_with_gpu_role_but_no_dgx_role_denied(client):
    response = client.post("/jobs/evaluate", json={
        "user_id": "u1", "gpus": 1, "partition": "dgx-a100", "roles": ["gpu_user"],
    })
    data = response.json()
    assert data["allow"] is False
    assert data["reason"] == "dgx partition denied"


def test_dgx_request_with_both_roles_allowed(client):
    response = client.post("/jobs/evaluate", json={
        "user_id": "u1", "gpus": 1, "partition": "dgx-a100",
        "roles": ["gpu_user", "dgx_access"],
    })
    assert response.json()["allow"] is True


# ---------------------------------------------------------------------------
# Validation edge cases
# ---------------------------------------------------------------------------

def test_missing_user_id_rejected(client):
    response = client.post("/jobs/evaluate", json={"gpus": 1})
    assert response.status_code == 422


def test_empty_body_rejected(client):
    response = client.post("/jobs/evaluate", json={})
    assert response.status_code == 422


def test_malformed_json_body_rejected(client):
    response = client.post(
        "/jobs/evaluate",
        content="{not valid json",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 422


def test_roles_as_wrong_type_rejected(client):
    """roles must be a list[str]; a bare string is not coerced into one."""
    response = client.post("/jobs/evaluate", json={"user_id": "u1", "roles": "gpu_user"})
    assert response.status_code == 422


def test_gpus_as_wrong_type_rejected(client):
    response = client.post("/jobs/evaluate", json={"user_id": "u1", "gpus": "not-a-number"})
    assert response.status_code == 422


def test_negative_gpus_accepted_and_treated_as_no_gpu_needed(client):
    """Characterizes current behavior (see test_core_gpu_source.py): there
    is no ge=0 constraint on gpus, and validate_gpu_access's `gpus <= 0`
    check means a negative value slips through as if no GPU was requested."""
    response = client.post("/jobs/evaluate", json={"user_id": "u1", "gpus": -1})
    assert response.status_code == 200
    assert response.json()["allow"] is True


def test_negative_memory_gb_accepted_without_validation(client):
    """Characterizes current behavior: memory_gb has no lower-bound
    constraint and is not used by evaluate_job's decision at all, so a
    negative value is accepted silently."""
    response = client.post("/jobs/evaluate", json={"user_id": "u1", "memory_gb": -16})
    assert response.status_code == 200


def test_unknown_extra_fields_are_ignored(client):
    """Characterizes current behavior: pydantic's default extra-field
    policy is "ignore", so an unrecognized field neither errors nor
    changes the decision."""
    response = client.post("/jobs/evaluate", json={
        "user_id": "u1", "not_a_real_field": "surprise",
    })
    assert response.status_code == 200
    assert response.json()["allow"] is True


def test_duplicate_role_entries_do_not_change_outcome(client):
    response = client.post("/jobs/evaluate", json={
        "user_id": "u1", "gpus": 1, "roles": ["gpu_user", "gpu_user", "gpu_user"],
    })
    assert response.json()["allow"] is True


# ---------------------------------------------------------------------------
# Authorization / org isolation
# ---------------------------------------------------------------------------

def test_org_id_accepted_but_has_no_effect_on_decision(client):
    """Audit finding: JobRequest.org_id exists on the model but
    evaluate_job() never reads it -- two requests that differ only in
    org_id get an identical decision. There is no organization/project
    isolation enforced by this endpoint; see PR description's
    "remaining gaps" note."""
    shared = {"user_id": "u1", "gpus": 1, "roles": ["gpu_user"], "partition": "dgx-a100"}
    resp_a = client.post("/jobs/evaluate", json={**shared, "org_id": "org-a"})
    resp_b = client.post("/jobs/evaluate", json={**shared, "org_id": "org-b"})
    assert resp_a.json() == resp_b.json()


def test_missing_org_id_defaults_to_none_and_still_evaluates(client):
    response = client.post("/jobs/evaluate", json={"user_id": "u1"})
    assert response.status_code == 200


def test_empty_user_id_string_is_accepted_by_validation(client):
    """Characterizes current behavior: user_id has no min_length constraint,
    so an empty string is a valid (if meaningless) identity."""
    response = client.post("/jobs/evaluate", json={"user_id": ""})
    assert response.status_code == 200


def test_user_id_wrong_type_rejected(client):
    response = client.post("/jobs/evaluate", json={"user_id": 12345})
    assert response.status_code == 422
