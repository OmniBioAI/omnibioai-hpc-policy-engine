"""Unit tests for QuotaService.evaluate as a whole: GPU access by role, DGX
partition access by role, and CPU and GPU quota limits, using mocked usage and
request objects with no database.

Developer: Manish Kumar <manish@omnibioai.org>
"""
import pytest
from unittest.mock import MagicMock
from app.services.quota_service import QuotaService
from app.models.decision import Decision
from app.models.quota import QuotaCheck


def _usage(cpu_hours=0.0, gpu_hours=0.0):
    """Build a mock usage record with the given CPU and GPU hours."""
    u = MagicMock()
    u.cpu_hours = cpu_hours
    u.gpu_hours = gpu_hours
    return u


def _request(gpus=0, partition="cpu", cpu_hours=1.0, gpu_hours=0.0):
    """Build a mock request with the given GPU count, partition and CPU and GPU hours."""
    r = MagicMock()
    r.gpus = gpus
    r.partition = partition
    r.cpu_hours = cpu_hours
    r.gpu_hours = gpu_hours
    return r


# ---------------------------------------------------------------------------
# GPU access validation
# ---------------------------------------------------------------------------

def test_no_gpu_needed_always_passes():
    """A request that needs no GPUs is allowed without a GPU role."""
    decision = QuotaService.evaluate(
        usage=_usage(),
        request=_request(gpus=0),
        roles=["researcher"],
    )
    assert decision.allow is True


def test_gpu_request_denied_without_gpu_user_role():
    """A GPU request without the gpu_user role is denied with a reason mentioning gpu."""
    decision = QuotaService.evaluate(
        usage=_usage(),
        request=_request(gpus=2),
        roles=["researcher"],
    )
    assert decision.allow is False
    assert "gpu" in decision.reason.lower()


def test_gpu_request_allowed_with_gpu_user_role():
    """A GPU request from a caller holding the gpu_user role is allowed."""
    decision = QuotaService.evaluate(
        usage=_usage(),
        request=_request(gpus=2, gpu_hours=1.0),
        roles=["researcher", "gpu_user"],
    )
    assert decision.allow is True


# ---------------------------------------------------------------------------
# Partition access validation
# ---------------------------------------------------------------------------

def test_dgx_a100_denied_without_dgx_access():
    """A request for the dgx-a100 partition without the dgx_access role is denied with a reason
    mentioning dgx.
    """
    decision = QuotaService.evaluate(
        usage=_usage(),
        request=_request(partition="dgx-a100"),
        roles=["researcher", "gpu_user"],
    )
    assert decision.allow is False
    assert "dgx" in decision.reason.lower()


def test_dgx_a100_allowed_with_dgx_access():
    """A request for the dgx-a100 partition with the dgx_access role is allowed."""
    decision = QuotaService.evaluate(
        usage=_usage(),
        request=_request(gpus=0, partition="dgx-a100"),
        roles=["researcher", "gpu_user", "dgx_access"],
    )
    assert decision.allow is True


def test_standard_partition_requires_no_special_role():
    """A standard partition is allowed without any special role."""
    decision = QuotaService.evaluate(
        usage=_usage(),
        request=_request(partition="cpu"),
        roles=[],
    )
    assert decision.allow is True


# ---------------------------------------------------------------------------
# Quota enforcement
# ---------------------------------------------------------------------------

def test_cpu_quota_exceeded_denied():
    """A request that exceeds the remaining CPU hours is denied with a reason mentioning cpu."""
    decision = QuotaService.evaluate(
        usage=_usage(cpu_hours=119.0),  # 1 hour remaining
        request=_request(cpu_hours=2.0),  # requesting 2
        roles=[],
    )
    assert decision.allow is False
    assert "cpu" in decision.reason.lower()


def test_gpu_quota_exceeded_denied():
    """A request that exceeds the remaining GPU hours is denied with a reason mentioning gpu."""
    decision = QuotaService.evaluate(
        usage=_usage(gpu_hours=23.5),  # 0.5 hours remaining
        request=_request(gpus=1, gpu_hours=1.0, partition="cpu"),
        roles=["gpu_user"],
    )
    assert decision.allow is False
    assert "gpu" in decision.reason.lower()


def test_quota_ok_within_limits():
    """A request within both quota limits is allowed with reason "quota ok"."""
    decision = QuotaService.evaluate(
        usage=_usage(cpu_hours=10.0, gpu_hours=5.0),
        request=_request(gpus=1, cpu_hours=5.0, gpu_hours=1.0),
        roles=["gpu_user"],
    )
    assert decision.allow is True
    assert decision.reason == "quota ok"


def test_decision_includes_remaining_hours():
    """The decision reports the remaining hours as the limit minus current usage (100 CPU and 20 GPU
    hours), not minus the requested hours.
    """
    # evaluate_quota returns (limit - current_used), not (limit - used - requested)
    decision = QuotaService.evaluate(
        usage=_usage(cpu_hours=20.0, gpu_hours=4.0),
        request=_request(cpu_hours=10.0, gpu_hours=2.0),
        roles=[],
    )
    assert decision.allow is True
    assert decision.remaining_cpu_hours == 100.0  # 120 - 20
    assert decision.remaining_gpu_hours == 20.0   # 24 - 4


def test_zero_request_always_passes():
    """A zero-hour request is allowed."""
    decision = QuotaService.evaluate(
        usage=_usage(cpu_hours=0.0, gpu_hours=0.0),
        request=_request(cpu_hours=0.0, gpu_hours=0.0),
        roles=[],
    )
    assert decision.allow is True
