"""
Use conftest.py fixtures directly so their bodies are executed and counted
by coverage.  Covers conftest.py lines: 22, 27-32, 37-40, 46-54.
"""
from unittest.mock import MagicMock, patch
from app.models.decision import Decision


# ---------------------------------------------------------------------------
# mock_db fixture  (conftest.py:22)
# ---------------------------------------------------------------------------

def test_mock_db_is_mock_instance(mock_db):
    assert isinstance(mock_db, MagicMock)


def test_mock_db_supports_arbitrary_attribute_access(mock_db):
    _ = mock_db.some_attr
    mock_db.some_method()
    mock_db.some_method.assert_called_once()


# ---------------------------------------------------------------------------
# mock_usage_record fixture  (conftest.py:27-32)
# ---------------------------------------------------------------------------

def test_mock_usage_record_user_id(mock_usage_record):
    assert mock_usage_record.user_id == "u1"


def test_mock_usage_record_zero_cpu_hours(mock_usage_record):
    assert mock_usage_record.cpu_hours == 0.0


def test_mock_usage_record_zero_gpu_hours(mock_usage_record):
    assert mock_usage_record.gpu_hours == 0.0


def test_mock_usage_record_zero_jobs_running(mock_usage_record):
    assert mock_usage_record.jobs_running == 0


# ---------------------------------------------------------------------------
# policy_client fixture  (conftest.py:37-40)
# ---------------------------------------------------------------------------

def test_policy_client_evaluate_returns_200(policy_client):
    response = policy_client.post("/jobs/evaluate", json={"user_id": "u-fixture"})
    assert response.status_code == 200


def test_policy_client_evaluate_allows_job(policy_client):
    response = policy_client.post("/jobs/evaluate", json={"user_id": "u-fixture"})
    assert response.json()["allow"] is True


def test_policy_client_evaluate_missing_user_id_returns_422(policy_client):
    response = policy_client.post("/jobs/evaluate", json={"cpu_hours": 2.0})
    assert response.status_code == 422


def test_policy_client_evaluate_returns_partition(policy_client):
    response = policy_client.post("/jobs/evaluate", json={
        "user_id": "u-fixture",
        "partition": "gpu",
    })
    assert response.json()["partition"] == "gpu"


# ---------------------------------------------------------------------------
# quota_client fixture  (conftest.py:46-54)
# ---------------------------------------------------------------------------

def test_quota_client_is_tuple_of_client_and_db(quota_client):
    tc, db = quota_client
    assert isinstance(db, MagicMock)


def test_quota_client_check_allow(quota_client):
    tc, mock_db = quota_client
    usage = MagicMock(cpu_hours=10.0, gpu_hours=2.0)
    decision = Decision(
        allow=True,
        reason="quota ok",
        remaining_cpu_hours=110.0,
        remaining_gpu_hours=22.0,
    )
    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage), \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=decision):
        response = tc.post("/quota/check", json={
            "user_id": "u-fixture",
            "cpu_hours": 1.0,
            "gpu_hours": 0.0,
            "gpus": 0,
        })
    assert response.status_code == 200
    assert response.json()["allow"] is True


def test_quota_client_check_deny(quota_client):
    tc, mock_db = quota_client
    usage = MagicMock(cpu_hours=119.0, gpu_hours=0.0)
    decision = Decision(
        allow=False,
        reason="cpu quota exceeded",
        remaining_cpu_hours=1.0,
        remaining_gpu_hours=24.0,
    )
    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage), \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=decision):
        response = tc.post("/quota/check", json={
            "user_id": "u-fixture2",
            "cpu_hours": 5.0,
            "gpu_hours": 0.0,
            "gpus": 0,
        })
    assert response.status_code == 200
    assert response.json()["allow"] is False
    assert "cpu" in response.json()["reason"].lower()


def test_quota_client_db_dependency_injected(quota_client):
    tc, mock_db = quota_client
    usage = MagicMock(cpu_hours=0.0, gpu_hours=0.0)
    decision = Decision(
        allow=True,
        reason="quota ok",
        remaining_cpu_hours=120.0,
        remaining_gpu_hours=24.0,
    )
    with patch("app.api.routes_quota.UsageService.get_or_create_user_usage",
               return_value=usage) as mock_svc, \
         patch("app.api.routes_quota.QuotaService.evaluate",
               return_value=decision):
        tc.post("/quota/check", json={"user_id": "u-db-check", "cpu_hours": 0.0,
                                      "gpu_hours": 0.0, "gpus": 0})
    mock_svc.assert_called_once_with(mock_db, "u-db-check")
