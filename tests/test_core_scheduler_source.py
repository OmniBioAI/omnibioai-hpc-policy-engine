"""
Direct-source unit tests for app/core/scheduler.py::SchedulerAdapter.

Loaded via tests/_srcload.py (see that module's docstring) so its lines are
measured even where the checked-in .so shadows the .py import.

Audit note: SchedulerAdapter is not a real Slurm/PBS/LSF/Kubernetes/cloud
integration -- get_cluster_load() is a stub that always returns the same
hardcoded dict, with no network/subprocess call, no error handling, no
timeout, and no retry logic. There is nothing to mock and no failure path
to exercise here (see PR description "remaining gaps" / "infrastructure
limitations" for the corresponding audit note); these tests characterize
the stub's actual current behavior rather than inventing scheduler-failure
scenarios the code doesn't implement. SchedulerAdapter/SchedulerService are
also not wired into any API route (grep of app/api/ finds no reference to
either), so there is no HTTP-level test to add for them.
"""
import asyncio

from tests._srcload import load

scheduler = load("app/core/scheduler.py")


def test_get_cluster_load_returns_expected_keys():
    result = asyncio.run(scheduler.SchedulerAdapter().get_cluster_load())
    assert set(result.keys()) == {"cpu_load", "gpu_load", "running_jobs"}


def test_get_cluster_load_values_are_stable_stub_values():
    result = asyncio.run(scheduler.SchedulerAdapter().get_cluster_load())
    assert result == {"cpu_load": 0.45, "gpu_load": 0.60, "running_jobs": 21}


def test_get_cluster_load_is_independent_across_instances():
    a = asyncio.run(scheduler.SchedulerAdapter().get_cluster_load())
    b = asyncio.run(scheduler.SchedulerAdapter().get_cluster_load())
    assert a == b
