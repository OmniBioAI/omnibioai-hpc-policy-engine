"""
Direct-source unit tests for app/core/policies.py::validate_partition_access.

Loaded via tests/_srcload.py (see that module's docstring) so its lines are
measured even where the checked-in .so shadows the .py import.
"""
from tests._srcload import load

policies = load("app/core/policies.py")


def test_dgx_partition_denied_without_dgx_access_role():
    ok, reason = policies.validate_partition_access([], "dgx-a100")
    assert ok is False
    assert reason == "dgx partition denied"


def test_dgx_partition_denied_with_unrelated_roles():
    ok, _reason = policies.validate_partition_access(["gpu_user", "researcher"], "dgx-a100")
    assert ok is False


def test_dgx_partition_allowed_with_dgx_access_role():
    ok, reason = policies.validate_partition_access(["dgx_access"], "dgx-a100")
    assert ok is True
    assert reason == "partition allowed"


def test_cpu_partition_allowed_with_no_roles():
    ok, _reason = policies.validate_partition_access([], "cpu")
    assert ok is True


def test_gpu_partition_allowed_with_no_roles():
    """Only the literal 'dgx-a100' partition is gated -- any other partition
    name (including 'gpu') is allowed regardless of roles."""
    ok, _reason = policies.validate_partition_access([], "gpu")
    assert ok is True


def test_unknown_partition_name_allowed_by_default():
    """Characterizes current behavior: partition names aren't validated
    against an allow-list, so an unrecognized/typo'd partition passes
    through as allowed rather than being rejected."""
    ok, _reason = policies.validate_partition_access([], "totally-made-up-partition")
    assert ok is True


def test_empty_partition_string_allowed():
    ok, _reason = policies.validate_partition_access([], "")
    assert ok is True


def test_partition_check_is_case_sensitive():
    """'DGX-A100' does not match the literal 'dgx-a100' gate, so it's
    treated as an ungated partition and allowed."""
    ok, _reason = policies.validate_partition_access([], "DGX-A100")
    assert ok is True
