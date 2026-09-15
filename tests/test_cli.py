from __future__ import annotations

import json
from pathlib import Path

import pytest

from crush_analyze.cli import main


def test_list_modules_prints_json(capsys: pytest.CaptureFixture[str]) -> None:
    exit_code = main(["list-modules"])

    assert exit_code == 0
    modules = json.loads(capsys.readouterr().out)
    ids = {m["id"] for m in modules}
    assert "stub" in ids
    assert "get_installed_apps" in ids


def test_run_bundled_module_writes_contract_json_and_exits_zero(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")
    output = tmp_path / "out.json"

    exit_code = main(["run", "--module", "stub", "--input", str(tmp_path), "--output", str(output)])

    assert exit_code == 0
    result = json.loads(output.read_text())
    assert result["status"] == "ok"


def test_run_unknown_module_exits_two_without_writing_output(tmp_path: Path) -> None:
    output = tmp_path / "out.json"

    exit_code = main(["run", "--module", "nope", "--input", str(tmp_path), "--output", str(output)])

    assert exit_code == 2
    assert not output.exists()


def test_run_without_module_exits_nonzero(tmp_path: Path) -> None:
    output = tmp_path / "out.json"

    with pytest.raises(SystemExit):
        main(["run", "--input", str(tmp_path), "--output", str(output)])
