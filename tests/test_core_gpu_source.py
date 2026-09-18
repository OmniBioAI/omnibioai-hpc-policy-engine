"""
Direct-source unit tests for app/core/gpu.py::validate_gpu_access.

Loaded via tests/_srcload.py so its lines/branches are measured even on a
host where the checked-in .so shadows the .py import (see _srcload.py for
why). Behavior is already exercised indirectly via test_quota_service.py
and test_routes_policy.py; this file targets the function directly with the
full input space, including edge cases those higher-level tests don't hit.

Developer: Manish Kumar <manish@omnibioai.org>
"""
from tests._srcload import load

gpu = load("app/core/gpu.py")


def test_zero_gpus_needs_no_role():
    """Requesting zero GPUs is allowed for any roles, with reason "no gpu needed"."""
    ok, reason = gpu.validate_gpu_access([], 0)
    assert ok is True
    assert reason == "no gpu needed"


def test_negative_gpus_short_circuits_to_no_gpu_needed():
    """Characterizes current behavior: `gpus <= 0` is a single check, so a
    negative gpu count is (silently) treated the same as zero/none."""
    ok, reason = gpu.validate_gpu_access([], -3)
    assert ok is True
    assert reason == "no gpu needed"


def test_positive_gpus_without_any_roles_denied():
    """Requesting a GPU with no roles is denied with reason "gpu access denied"."""
    ok, reason = gpu.validate_gpu_access([], 1)
    assert ok is False
    assert reason == "gpu access denied"


def test_positive_gpus_with_unrelated_roles_denied():
    """Requesting a GPU with roles that do not include gpu_user is denied."""
    ok, _reason = gpu.validate_gpu_access(["researcher", "viewer"], 1)
    assert ok is False


def test_positive_gpus_with_gpu_user_role_allowed():
    """Requesting a GPU with the gpu_user role is allowed, with reason "gpu allowed"."""
    ok, reason = gpu.validate_gpu_access(["researcher", "gpu_user"], 1)
    assert ok is True
    assert reason == "gpu allowed"


def test_role_match_is_exact_not_substring():
    """'gpu_user_temp' must not satisfy the 'gpu_user' membership check."""
    ok, _reason = gpu.validate_gpu_access(["gpu_user_temp"], 1)
    assert ok is False


def test_role_match_is_case_sensitive():
    """The role "GPU_USER" does not satisfy the gpu_user requirement, so the GPU request is denied.
    """
    ok, _reason = gpu.validate_gpu_access(["GPU_USER"], 1)
    assert ok is False


def test_large_gpu_request_with_role_allowed():
    """A large GPU request (64 GPUs) is allowed for a gpu_user, since only the role is checked and
    not the count.
    """
    ok, _reason = gpu.validate_gpu_access(["gpu_user"], 64)
    assert ok is True


def test_empty_roles_list_with_zero_gpus_allowed():
    """An empty roles list with zero GPUs is allowed."""
    ok, _reason = gpu.validate_gpu_access([], 0)
    assert ok is True
