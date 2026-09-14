from __future__ import annotations

import json
from pathlib import Path

import pytest

from crush_analyze.cli import main


def test_list_modules_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["list-modules"])

    assert exit_code == 0
    modules = json.loads(capsys.readouterr().out)
    assert {m["id"] for m in modules} == {"stub"}


def test_run_bundled_module_writes_contract_json_and_exits_zero(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")
    output = tmp_path / "out.json"

    exit_code = main(["run", "--module", "stub", "--input", str(tmp_path), "--output", str(output)])

    assert exit_code == 0
    result = json.loads(output.read_text())
    assert result["status"] == "ok"
    assert result["run"]["dev_mode"] is False


def test_run_unknown_module_exits_two_without_writing_output(tmp_path: Path) -> None:
    output = tmp_path / "out.json"

    exit_code = main(["run", "--module", "nope", "--input", str(tmp_path), "--output", str(output)])

    assert exit_code == 2
    assert not output.exists()


def test_run_module_path_requires_dev_flag(tmp_path: Path) -> None:
    output = tmp_path / "out.json"

    with pytest.raises(SystemExit):
        main(["run", "--module-path", "x.py", "--input", str(tmp_path), "--output", str(output)])


def test_run_dev_mode_against_an_external_module(tmp_path: Path) -> None:
    module_file = tmp_path / "ext.py"
    module_file.write_text(
        "from crush_analyze.modules.base import ModuleInfo, ModuleResult\n"
        "\n"
        "def run(context):\n"
        "    return ModuleResult(columns=[], rows=[])\n"
        "\n"
        "MODULE = ModuleInfo(id='ext', name='Ext', module_version='1', run=run)\n"
    )
    output = tmp_path / "out.json"

    exit_code = main(
        [
            "run",
            "--module-path",
            str(module_file),
            "--dev",
            "--input",
            str(tmp_path),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    result = json.loads(output.read_text())
    assert result["run"]["dev_mode"] is True
    assert result["run"]["module_source"] == f"external:{module_file}"


def test_run_module_that_raises_exits_one(tmp_path: Path) -> None:
    module_file = tmp_path / "broken.py"
    module_file.write_text(
        "from crush_analyze.modules.base import ModuleInfo\n"
        "\n"
        "def run(context):\n"
        "    raise ValueError('boom')\n"
        "\n"
        "MODULE = ModuleInfo(id='broken', name='Broken', module_version='1', run=run)\n"
    )
    output = tmp_path / "out.json"

    exit_code = main(
        [
            "run",
            "--module-path",
            str(module_file),
            "--dev",
            "--input",
            str(tmp_path),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 1
    result = json.loads(output.read_text())
    assert result["status"] == "error"
