import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api.routes_policy import router


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


# ---------------------------------------------------------------------------
# POST /jobs/evaluate
# ---------------------------------------------------------------------------

def test_evaluate_job_allow_default(client):
    response = client.post("/jobs/evaluate", json={
        "user_id": "u1",
        "cpu_hours": 4.0,
        "gpu_hours": 0.0,
        "gpus": 0,
        "memory_gb": 16,
        "partition": "cpu",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["allow"] is True
    assert data["reason"] == "job approved"


def test_evaluate_job_returns_partition(client):
    response = client.post("/jobs/evaluate", json={
        "user_id": "u1",
        "partition": "gpu",
    })
    assert response.status_code == 200
    assert response.json()["partition"] == "gpu"


def test_evaluate_job_with_gpu_partition_and_gpu_user_role(client):
    response = client.post("/jobs/evaluate", json={
        "user_id": "u2",
        "gpus": 4,
        "gpu_hours": 2.0,
        "partition": "gpu",
        "roles": ["gpu_user"],
    })
    assert response.status_code == 200
    assert response.json()["allow"] is True


def test_evaluate_job_with_gpu_partition_denied_without_gpu_user_role(client):
    """PR12: /jobs/evaluate previously always approved regardless of gpus
    requested -- now wires up the (already-existing, already-tested)
    validate_gpu_access check, so a request for GPUs without the gpu_user
    role is denied instead of silently approved."""
    response = client.post("/jobs/evaluate", json={
        "user_id": "u2",
        "gpus": 4,
        "gpu_hours": 2.0,
        "partition": "gpu",
    })
    assert response.status_code == 200
    data = response.json()
    assert data["allow"] is False
    assert "gpu" in data["reason"].lower()


def test_evaluate_job_default_partition_is_cpu(client):
    response = client.post("/jobs/evaluate", json={"user_id": "u3"})
    assert response.status_code == 200
    assert response.json()["partition"] == "cpu"


def test_evaluate_job_dgx_partition_denied_without_roles(client):
    """PR12: no roles supplied -> denied at the gpu_user check first
    (validate_gpu_access runs before validate_partition_access), same
    order QuotaService.evaluate already used."""
    response = client.post("/jobs/evaluate", json={
        "user_id": "u4",
        "partition": "dgx-a100",
        "gpus": 8,
    })
    assert response.status_code == 200
    data = response.json()
    assert data["allow"] is False
    assert "gpu" in data["reason"].lower()


def test_evaluate_job_dgx_partition_denied_without_dgx_access_role(client):
    response = client.post("/jobs/evaluate", json={
        "user_id": "u4",
        "partition": "dgx-a100",
        "gpus": 8,
        "roles": ["gpu_user"],  # passes gpu check, still lacks dgx_access
    })
    assert response.status_code == 200
    data = response.json()
    assert data["allow"] is False
    assert "dgx" in data["reason"].lower()


def test_evaluate_job_dgx_partition_allowed_with_both_roles(client):
    response = client.post("/jobs/evaluate", json={
        "user_id": "u4",
        "partition": "dgx-a100",
        "gpus": 8,
        "roles": ["gpu_user", "dgx_access"],
    })
    assert response.status_code == 200
    assert response.json()["allow"] is True


def test_evaluate_job_missing_user_id_returns_422(client):
    response = client.post("/jobs/evaluate", json={"cpu_hours": 4.0})
    assert response.status_code == 422
