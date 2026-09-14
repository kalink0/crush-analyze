from __future__ import annotations

from pathlib import Path

from crush_analyze.modules import get_module
from crush_analyze.runner import ModuleLoadError, load_external_module, run
from crush_analyze.modules.base import ModuleInfo, ModuleResult


def test_run_stub_module_returns_ok_status(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")

    result = run(get_module("stub"), tmp_path, dev_mode=False, module_source="bundled")

    assert result["status"] == "ok"
    assert result["rows"] == [{"_row_status": "ok", "path": str(tmp_path / "a.txt")}]


def test_run_catches_an_exception_from_the_module_as_error_status(tmp_path: Path) -> None:
    def broken_run(context: object) -> ModuleResult:
        raise ValueError("boom")

    broken = ModuleInfo(id="broken", name="Broken", module_version="1", run=broken_run)

    result = run(broken, tmp_path, dev_mode=False, module_source="bundled")

    assert result["status"] == "error"
    assert result["error"] == {"message": "boom", "detail": "ValueError"}
    assert result["rows"] == []


def test_load_external_module_reads_a_module_level_module_constant(tmp_path: Path) -> None:
    module_file = tmp_path / "my_module.py"
    module_file.write_text(
        "from crush_analyze.modules.base import ModuleInfo, ModuleResult\n"
        "from crush_analyze.contract import Column\n"
        "\n"
        "def run(context):\n"
        "    return ModuleResult(columns=[Column('x', 'X', 'string')], rows=[])\n"
        "\n"
        "MODULE = ModuleInfo(id='my_module', name='My Module', module_version='1', run=run)\n"
    )

    info = load_external_module(module_file)

    assert info.id == "my_module"


def test_load_external_module_rejects_a_missing_file(tmp_path: Path) -> None:
    try:
        load_external_module(tmp_path / "missing.py")
        assert False, "expected ModuleLoadError"
    except ModuleLoadError:
        pass


def test_load_external_module_rejects_a_file_without_module_constant(tmp_path: Path) -> None:
    module_file = tmp_path / "no_module.py"
    module_file.write_text("x = 1\n")

    try:
        load_external_module(module_file)
        assert False, "expected ModuleLoadError"
    except ModuleLoadError:
        pass
