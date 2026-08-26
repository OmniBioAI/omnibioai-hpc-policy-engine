"""
Direct-source unit tests for app/services/quota_service.py::QuotaService.

Loaded via tests/_srcload.py (see that module's docstring) so its own lines
are measured even where the checked-in .so shadows the .py import. The
module-level `from app.core.gpu import validate_gpu_access` (etc.) inside
quota_service.py still resolves through normal package import machinery --
i.e. it calls whatever app.core.gpu/policies/quota normally resolve to on
this host (.so or .py) -- which is fine: those modules' own lines are
measured independently by test_core_gpu_source.py / test_core_policies_source.py
/ test_core_quota_source.py, and their logic is Cython-compiled as-is from
the same .py source, so behavior is identical either way.

Scenarios mirror tests/test_quota_service.py (kept intact, not modified);
this file adds check-ordering/precedence coverage that file doesn't target.
"""
from unittest.mock import MagicMock, patch

from tests._srcload import load

quota_service_mod = load("app/services/quota_service.py")
QuotaService = quota_service_mod.QuotaService


def _usage(cpu_hours=0.0, gpu_hours=0.0):
    u = MagicMock()
    u.cpu_hours = cpu_hours
    u.gpu_hours = gpu_hours
    return u


def _request(gpus=0, partition="cpu", cpu_hours=1.0, gpu_hours=0.0):
    r = MagicMock()
    r.gpus = gpus
    r.partition = partition
    r.cpu_hours = cpu_hours
    r.gpu_hours = gpu_hours
    return r


def test_gpu_denied_short_circuits_before_partition_and_quota_checks():
    """When the gpu check fails, validate_partition_access and
    evaluate_quota must not run at all."""
    with patch.object(quota_service_mod, "validate_partition_access") as mock_partition, \
         patch.object(quota_service_mod, "evaluate_quota") as mock_quota:
        decision = QuotaService.evaluate(
            usage=_usage(),
            request=_request(gpus=2, partition="dgx-a100"),
            roles=[],
        )
    assert decision.allow is False
    assert decision.reason == "gpu access denied"
    mock_partition.assert_not_called()
    mock_quota.assert_not_called()


def test_partition_denied_short_circuits_before_quota_check():
    """When gpu passes but partition fails, evaluate_quota must not run."""
    with patch.object(quota_service_mod, "evaluate_quota") as mock_quota:
        decision = QuotaService.evaluate(
            usage=_usage(),
            request=_request(gpus=0, partition="dgx-a100"),
            roles=[],
        )
    assert decision.allow is False
    assert decision.reason == "dgx partition denied"
    mock_quota.assert_not_called()


def test_all_checks_pass_falls_through_to_quota_result():
    decision = QuotaService.evaluate(
        usage=_usage(cpu_hours=10.0, gpu_hours=5.0),
        request=_request(gpus=1, partition="cpu", cpu_hours=5.0, gpu_hours=1.0),
        roles=["gpu_user"],
    )
    assert decision.allow is True
    assert decision.reason == "quota ok"


def test_denied_decision_has_zero_remaining_hours_defaults():
    """When denied at the gpu/partition stage (before evaluate_quota runs),
    the Decision falls back to its model defaults (0) for remaining hours
    rather than reporting the caller's real remaining budget."""
    decision = QuotaService.evaluate(
        usage=_usage(cpu_hours=1.0, gpu_hours=1.0),
        request=_request(gpus=2, partition="cpu"),
        roles=[],
    )
    assert decision.allow is False
    assert decision.remaining_cpu_hours == 0
    assert decision.remaining_gpu_hours == 0


def test_quota_exceeded_after_passing_gpu_and_partition_checks():
    decision = QuotaService.evaluate(
        usage=_usage(cpu_hours=119.5),
        request=_request(gpus=0, partition="cpu", cpu_hours=1.0),
        roles=[],
    )
    assert decision.allow is False
    assert decision.reason == "cpu quota exceeded"


def test_returns_decision_instance():
    from app.models.decision import Decision
    decision = QuotaService.evaluate(
        usage=_usage(),
        request=_request(),
        roles=[],
    )
    assert isinstance(decision, Decision)
