"""
Unit tests for app/core/config.py::Config.

Config.* are plain class attributes evaluated once, at module-exec time,
from os.getenv(...). To exercise different env-var combinations
deterministically (without mutating the single Config object every other
test file in this session imports via `app.core.config`), each test here
loads a *fresh* copy of config.py by file path (tests/_srcload.py) inside an
os.environ patch, so the env vars are only visible to that one exec and
nothing else in the suite is affected.
"""
import os
from unittest.mock import patch

from tests._srcload import load


def _load_config_with_env(env: dict):
    # os.environ is read at class-body execution time inside config.py, so
    # the patch must be active for the load() call itself.
    clean_env = {k: v for k, v in os.environ.items() if not k.startswith((
        "MYSQL_", "REDIS_URL", "DEFAULT_CPU_HOURS", "DEFAULT_GPU_HOURS", "MAX_CONCURRENT_JOBS",
    ))}
    with patch.dict(os.environ, {**clean_env, **env}, clear=True):
        return load("app/core/config.py")


# ---------------------------------------------------------------------------
# Safe defaults when nothing is configured
# ---------------------------------------------------------------------------

def test_defaults_used_when_no_env_vars_set():
    cfg = _load_config_with_env({})
    assert cfg.Config.MYSQL_HOST == "mysql"
    assert cfg.Config.MYSQL_PORT == 3306
    assert cfg.Config.MYSQL_DB == "omnibioai_hpc"
    assert cfg.Config.MYSQL_USER == "root"
    assert cfg.Config.MYSQL_PASSWORD == "root"
    assert cfg.Config.REDIS_URL == "redis://redis:6379"
    assert cfg.Config.DEFAULT_CPU_HOURS == 120
    assert cfg.Config.DEFAULT_GPU_HOURS == 24
    assert cfg.Config.MAX_CONCURRENT_JOBS == 5
    assert cfg.Config.APP_NAME == "OmniBioAI HPC Policy Engine"


# ---------------------------------------------------------------------------
# Valid overrides
# ---------------------------------------------------------------------------

def test_env_vars_override_defaults():
    cfg = _load_config_with_env({
        "MYSQL_HOST": "db.internal",
        "MYSQL_PORT": "5432",
        "MYSQL_DB": "custom_db",
        "MYSQL_USER": "svc",
        "MYSQL_PASSWORD": "hunter2",
        "REDIS_URL": "redis://cache:6380",
        "DEFAULT_CPU_HOURS": "500",
        "DEFAULT_GPU_HOURS": "50",
        "MAX_CONCURRENT_JOBS": "20",
    })
    assert cfg.Config.MYSQL_HOST == "db.internal"
    assert cfg.Config.MYSQL_PORT == 5432
    assert cfg.Config.MYSQL_DB == "custom_db"
    assert cfg.Config.MYSQL_USER == "svc"
    assert cfg.Config.MYSQL_PASSWORD == "hunter2"
    assert cfg.Config.REDIS_URL == "redis://cache:6380"
    assert cfg.Config.DEFAULT_CPU_HOURS == 500
    assert cfg.Config.DEFAULT_GPU_HOURS == 50
    assert cfg.Config.MAX_CONCURRENT_JOBS == 20


def test_zero_quota_defaults_are_respected_verbatim():
    """A deliberately-zeroed quota env var is honored, not silently
    replaced by a nonzero default."""
    cfg = _load_config_with_env({"DEFAULT_CPU_HOURS": "0", "DEFAULT_GPU_HOURS": "0"})
    assert cfg.Config.DEFAULT_CPU_HOURS == 0
    assert cfg.Config.DEFAULT_GPU_HOURS == 0


# ---------------------------------------------------------------------------
# Invalid configuration -- no graceful handling exists (audit gap)
# ---------------------------------------------------------------------------

def test_non_numeric_mysql_port_raises_at_import_time():
    """Characterizes current behavior: MYSQL_PORT is parsed with a bare
    int(...) call and nothing catches a malformed value -- the module fails
    to import at all (ValueError) rather than falling back to the default
    or raising a clear configuration error. Documented as a "bugs
    discovered but not fixed" item in the PR description; not fixed here
    per the test-only scope of this change."""
    import pytest
    with pytest.raises(ValueError):
        _load_config_with_env({"MYSQL_PORT": "not-a-port"})


def test_non_numeric_default_cpu_hours_raises_at_import_time():
    import pytest
    with pytest.raises(ValueError):
        _load_config_with_env({"DEFAULT_CPU_HOURS": "unlimited"})


def test_non_numeric_max_concurrent_jobs_raises_at_import_time():
    import pytest
    with pytest.raises(ValueError):
        _load_config_with_env({"MAX_CONCURRENT_JOBS": "many"})


def test_empty_string_mysql_host_is_accepted_verbatim():
    """Characterizes current behavior: string-typed settings have no
    non-empty validation, so an explicitly-empty value is accepted as-is."""
    cfg = _load_config_with_env({"MYSQL_HOST": ""})
    assert cfg.Config.MYSQL_HOST == ""
