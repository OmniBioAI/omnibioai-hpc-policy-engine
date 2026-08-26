"""
Pydantic model validation tests for app/models/{decision,job,quota}.py.

These models aren't Cython-compiled (not in setup.py's EXTENSIONS list), so
they're already traced normally by coverage; this file targets validation
behavior -- defaults, required fields, type coercion, and the absence of
value constraints -- that the route-level tests don't exhaustively cover.
"""
import pytest
from pydantic import ValidationError

from app.models.decision import Decision
from app.models.job import JobRequest
from app.models.quota import QuotaCheck

# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------

def test_decision_requires_allow_and_reason():
    with pytest.raises(ValidationError):
        Decision()


def test_decision_remaining_hours_default_to_zero():
    d = Decision(allow=True, reason="ok")
    assert d.remaining_cpu_hours == 0
    assert d.remaining_gpu_hours == 0


def test_decision_reason_must_be_string():
    with pytest.raises(ValidationError):
        Decision(allow=True, reason=123)


# ---------------------------------------------------------------------------
# JobRequest
# ---------------------------------------------------------------------------

def test_job_request_requires_user_id():
    with pytest.raises(ValidationError):
        JobRequest()


def test_job_request_defaults():
    r = JobRequest(user_id="u1")
    assert r.cpu_hours == 0
    assert r.gpu_hours == 0
    assert r.gpus == 0
    assert r.memory_gb == 0
    assert r.partition == "cpu"
    assert r.roles == []
    assert r.org_id is None


def test_job_request_numeric_string_coerced_to_float():
    r = JobRequest(user_id="u1", cpu_hours="4.5")
    assert r.cpu_hours == 4.5


def test_job_request_negative_values_accepted_no_lower_bound():
    """No ge=0 constraint exists on any resource field."""
    r = JobRequest(user_id="u1", cpu_hours=-1, gpu_hours=-1, gpus=-1, memory_gb=-1)
    assert r.cpu_hours == -1
    assert r.gpus == -1


def test_job_request_roles_default_is_not_shared_between_instances():
    """Guards against a mutable-default-argument style bug: two instances
    must not share the same underlying roles list object."""
    a = JobRequest(user_id="a")
    b = JobRequest(user_id="b")
    a.roles.append("gpu_user")
    assert b.roles == []


def test_job_request_roles_reject_non_string_items():
    with pytest.raises(ValidationError):
        JobRequest(user_id="u1", roles=[1, 2, 3])


def test_job_request_org_id_accepts_none_explicitly():
    r = JobRequest(user_id="u1", org_id=None)
    assert r.org_id is None


# ---------------------------------------------------------------------------
# QuotaCheck
# ---------------------------------------------------------------------------

def test_quota_check_requires_user_id():
    with pytest.raises(ValidationError):
        QuotaCheck()


def test_quota_check_defaults():
    q = QuotaCheck(user_id="u1")
    assert q.cpu_hours == 0
    assert q.gpu_hours == 0
    assert q.gpus == 0
    assert q.partition == "cpu"
    assert q.roles == []


def test_quota_check_has_no_org_id_field():
    """Audit finding: unlike JobRequest, QuotaCheck has no org_id field at
    all -- /quota/check has no organization/project-scoping concept
    whatsoever, not even an unused one. See PR description's "remaining
    gaps" note."""
    q = QuotaCheck(user_id="u1")
    assert not hasattr(q, "org_id")


def test_quota_check_negative_values_accepted_no_lower_bound():
    q = QuotaCheck(user_id="u1", cpu_hours=-5, gpu_hours=-5, gpus=-5)
    assert q.cpu_hours == -5


def test_quota_check_roles_reject_non_string_items():
    with pytest.raises(ValidationError):
        QuotaCheck(user_id="u1", roles=[{"not": "a string"}])
