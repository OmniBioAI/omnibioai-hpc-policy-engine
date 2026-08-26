"""
Direct-source unit tests for app/services/scheduler_service.py::SchedulerService.

Loaded via tests/_srcload.py (see that module's docstring) so its lines are
measured even where the checked-in .so shadows the .py import.

Audit note: SchedulerService is not referenced anywhere under app/api/, so
it is not reachable through any HTTP endpoint -- these are plain unit tests
of the class itself. See test_core_scheduler_source.py for why there is no
scheduler-failure path to test (SchedulerAdapter is a hardcoded stub).
"""
import asyncio

from tests._srcload import load

scheduler_service_mod = load("app/services/scheduler_service.py")
SchedulerService = scheduler_service_mod.SchedulerService


def test_init_creates_a_scheduler_adapter():
    svc = SchedulerService()
    assert svc.scheduler.__class__.__name__ == "SchedulerAdapter"


def test_cluster_status_delegates_to_adapter():
    svc = SchedulerService()
    result = asyncio.run(svc.cluster_status())
    assert result == {"cpu_load": 0.45, "gpu_load": 0.60, "running_jobs": 21}


def test_each_instance_gets_its_own_adapter():
    a = SchedulerService()
    b = SchedulerService()
    assert a.scheduler is not b.scheduler
