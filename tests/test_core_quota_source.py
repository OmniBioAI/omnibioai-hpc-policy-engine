"""
Direct-source unit tests for app/core/quota.py::evaluate_quota.

Loaded via tests/_srcload.py (see that module's docstring) so its lines are
measured even where the checked-in .so shadows the .py import.

evaluate_quota reads its limits from app.core.config.Config at call time
(Config.DEFAULT_CPU_HOURS / DEFAULT_GPU_HOURS are plain class attributes),
so tests patch those attributes directly to pin deterministic limits rather
than depending on whatever env vars happen to be set for the process.
"""
from unittest.mock import patch

from tests._srcload import load

quota = load("app/core/quota.py")


def _patched_limits(cpu_limit, gpu_limit):
    return patch.multiple(
        quota.Config,
        DEFAULT_CPU_HOURS=cpu_limit,
        DEFAULT_GPU_HOURS=gpu_limit,
    )


# ---------------------------------------------------------------------------
# Within-limits / boundary behavior
# ---------------------------------------------------------------------------

def test_within_both_limits_allowed():
    with _patched_limits(100, 20):
        ok, reason, rem_cpu, rem_gpu = quota.evaluate_quota(10, 5, 5, 5)
    assert ok is True
    assert reason == "quota ok"
    assert rem_cpu == 90
    assert rem_gpu == 15


def test_request_exactly_equal_to_remaining_cpu_is_allowed():
    """Boundary: the check is strictly `>`, so a request equal to what's
    left is not an overage."""
    with _patched_limits(100, 20):
        ok, _reason, rem_cpu, _rem_gpu = quota.evaluate_quota(90, 0, 10, 0)
    assert ok is True
    assert rem_cpu == 10


def test_request_one_over_remaining_cpu_denied():
    with _patched_limits(100, 20):
        ok, reason, _rem_cpu, _rem_gpu = quota.evaluate_quota(90, 0, 10.0001, 0)
    assert ok is False
    assert reason == "cpu quota exceeded"


def test_request_exactly_equal_to_remaining_gpu_is_allowed():
    with _patched_limits(100, 20):
        ok, _reason, _rem_cpu, rem_gpu = quota.evaluate_quota(0, 15, 0, 5)
    assert ok is True
    assert rem_gpu == 5


def test_request_one_over_remaining_gpu_denied():
    with _patched_limits(100, 20):
        ok, reason, _rem_cpu, _rem_gpu = quota.evaluate_quota(0, 15, 0, 5.0001)
    assert ok is False
    assert reason == "gpu quota exceeded"


# ---------------------------------------------------------------------------
# Exceeded quota
# ---------------------------------------------------------------------------

def test_cpu_exceeded_denies_before_checking_gpu():
    """cpu is checked first: a request that blows both budgets is reported
    as a cpu overage, not a gpu one."""
    with _patched_limits(10, 10):
        ok, reason, _rem_cpu, _rem_gpu = quota.evaluate_quota(9, 9, 5, 5)
    assert ok is False
    assert reason == "cpu quota exceeded"


def test_gpu_exceeded_when_cpu_is_within_limits():
    with _patched_limits(100, 10):
        ok, reason, _rem_cpu, _rem_gpu = quota.evaluate_quota(0, 9, 1, 5)
    assert ok is False
    assert reason == "gpu quota exceeded"


def test_remaining_hours_reported_even_when_denied():
    """The (remaining_cpu, remaining_gpu) tuple reflects current usage vs.
    the limit -- not usage vs. the (denied) request -- regardless of the
    allow/deny outcome."""
    with _patched_limits(100, 20):
        ok, _reason, rem_cpu, rem_gpu = quota.evaluate_quota(95, 0, 10, 0)
    assert ok is False
    assert rem_cpu == 5
    assert rem_gpu == 20


# ---------------------------------------------------------------------------
# Zero / negative / already-over-budget edge cases
# ---------------------------------------------------------------------------

def test_zero_request_always_allowed_even_at_zero_remaining():
    with _patched_limits(10, 10):
        ok, _reason, rem_cpu, rem_gpu = quota.evaluate_quota(10, 10, 0, 0)
    assert ok is True
    assert rem_cpu == 0
    assert rem_gpu == 0


def test_usage_already_over_limit_denies_any_positive_request():
    """current usage can already exceed the configured limit (e.g. the
    limit was lowered after usage accrued); remaining goes negative, and
    any positive request is denied."""
    with _patched_limits(10, 10):
        ok, _reason, rem_cpu, _rem_gpu = quota.evaluate_quota(15, 0, 0.01, 0)
    assert ok is False
    assert rem_cpu == -5


def test_negative_request_is_allowed_through():
    """Characterizes current behavior: there is no floor/validation on the
    requested amount, so a negative request_cpu is always <= remaining and
    is silently allowed (no guard against malformed/negative input)."""
    with _patched_limits(10, 10):
        ok, _reason, _rem_cpu, _rem_gpu = quota.evaluate_quota(0, 0, -5, 0)
    assert ok is True


def test_negative_current_usage_inflates_remaining():
    """Characterizes current behavior: negative recorded usage (e.g. a data
    bug) is not clamped and simply inflates the remaining budget."""
    with _patched_limits(10, 10):
        ok, _reason, rem_cpu, _rem_gpu = quota.evaluate_quota(-5, 0, 14, 0)
    assert ok is True
    assert rem_cpu == 15
