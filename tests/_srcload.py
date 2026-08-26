"""
Test-only helper: import a module directly from its .py source file on disk,
bypassing normal package import resolution.

Why this exists: setup.py (see EXTENSIONS there) Cython-compiles eight
modules (app/core/gpu.py, policies.py, quota.py, scheduler.py,
app/services/quota_service.py, scheduler_service.py, and
app/api/routes_policy.py, routes_quota.py) into pre-built .so extensions
that are checked into git alongside their .py source, e.g.
app/core/gpu.cpython-313-aarch64-linux-gnu.so next to app/core/gpu.py.

CPython's default import machinery prefers a matching extension module over
a same-named .py file. On a host whose interpreter ABI/arch happens to match
the checked-in .so tag (cpython-313-aarch64-linux-gnu), a plain
`import app.core.gpu` silently resolves to the compiled .so, not the .py.
coverage.py cannot trace execution inside a compiled extension, so on such a
host those modules' lines never appear in a coverage report at all -- even
though their logic *is* being exercised (indirectly, through the compiled
binary) by tests that import them normally. On hosts where the .so tag does
not match (e.g. this repo's CI, which runs Python 3.11), the .so is skipped
automatically and the .py import already gets measured -- no workaround
needed there.

Loading the .py file directly by path (the same technique
tests/test_setup_module.py already uses for setup.py) sidesteps the .so/.py
shadowing so the real .py source is what gets executed and measured,
regardless of host architecture. It does not change any production
behavior -- Cython compiles these files essentially as-is, so the .py
source and the compiled extension implement the same logic.
"""
import importlib.util
import os

_REPO_ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))


def load(relative_path: str):
    """Load and return the .py module at `relative_path` (repo-root-relative)."""
    full_path = os.path.join(_REPO_ROOT, relative_path)
    module_name = "srcload_" + relative_path.replace("/", "_").replace(".", "_")
    spec = importlib.util.spec_from_file_location(module_name, full_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
