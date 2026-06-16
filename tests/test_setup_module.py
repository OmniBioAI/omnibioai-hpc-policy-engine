"""
Cover setup.py by importing it with Cython mocked out.

Module-level import covers: imports, Options.annotate, EXTENSIONS list,
def make_extensions, and the setup() call (which calls make_extensions
with the real EXTENSIONS list, covering the "file exists" branch).

Explicit tests cover the "file not found" branch (warning + skip).
"""
import os
import sys
import importlib.util
import pytest
from unittest.mock import MagicMock, patch

SETUP_PY = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "setup.py")
)


def _load_setup():
    """Exec setup.py with Cython mocked; real setuptools.extension is kept."""
    extra = {
        "Cython": MagicMock(),
        "Cython.Build": MagicMock(),
        "Cython.Compiler": MagicMock(),
    }
    with patch.dict(sys.modules, extra), \
         patch("setuptools.setup"), \
         patch("setuptools.find_packages", return_value=[]):
        sys.modules.pop("_hpc_setup_under_test", None)
        spec = importlib.util.spec_from_file_location("_hpc_setup_under_test", SETUP_PY)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


@pytest.fixture(scope="module")
def setup_mod():
    return _load_setup()


# ---------------------------------------------------------------------------
# Module-level attributes
# ---------------------------------------------------------------------------

def test_setup_module_has_make_extensions(setup_mod):
    assert callable(setup_mod.make_extensions)


def test_extensions_list_is_nonempty(setup_mod):
    assert isinstance(setup_mod.EXTENSIONS, list)
    assert len(setup_mod.EXTENSIONS) > 0


def test_extensions_entries_are_python_files(setup_mod):
    for path in setup_mod.EXTENSIONS:
        assert path.endswith(".py"), f"Expected .py, got: {path}"


# ---------------------------------------------------------------------------
# make_extensions — file exists branch (lines 31-32)
# ---------------------------------------------------------------------------

def test_make_extensions_returns_extension_for_existing_file(setup_mod, tmp_path):
    src = tmp_path / "mymod.py"
    src.write_text("x = 1")
    result = setup_mod.make_extensions([str(src)])
    assert len(result) == 1


def test_make_extensions_module_name_strips_py_suffix(setup_mod, tmp_path):
    src = tmp_path / "alpha.py"
    src.write_text("pass")
    result = setup_mod.make_extensions([str(src)])
    assert len(result) == 1
    ext = result[0]
    assert hasattr(ext, "name")
    assert not ext.name.endswith(".py")


# ---------------------------------------------------------------------------
# make_extensions — file not found branch (lines 28-30)
# ---------------------------------------------------------------------------

def test_make_extensions_skips_missing_file(setup_mod, capsys):
    result = setup_mod.make_extensions(["this_path_does_not_exist_xyz.py"])
    assert result == []
    captured = capsys.readouterr()
    assert "WARNING" in captured.out


def test_make_extensions_warning_contains_path(setup_mod, capsys):
    missing = "no_such_file_abc.py"
    setup_mod.make_extensions([missing])
    captured = capsys.readouterr()
    assert missing in captured.out


# ---------------------------------------------------------------------------
# make_extensions — mixed input
# ---------------------------------------------------------------------------

def test_make_extensions_mixed_existing_and_missing(setup_mod, tmp_path, capsys):
    existing = tmp_path / "real.py"
    existing.write_text("pass")
    result = setup_mod.make_extensions([str(existing), "nonexistent_file.py"])
    assert len(result) == 1
    captured = capsys.readouterr()
    assert "WARNING" in captured.out


def test_make_extensions_empty_list(setup_mod):
    result = setup_mod.make_extensions([])
    assert result == []
