from __future__ import annotations

from datetime import datetime, timezone

from crush_analyze.contract import Column, build_result


def test_build_result_has_mandatory_fields_on_success() -> None:
    result = build_result(
        analyzer_id="stub",
        analyzer_name="Stub",
        analyzer_platform="generic",
        analyzer_source=None,
        module_version="1",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration_ms=5,
        input_path="/tmp/in",
        source_files=["a"],
        status="ok",
        warnings=[],
        error=None,
        columns=[Column(key="path", label="Path", type="string")],
        rows=[{"_row_status": "ok", "path": "/tmp/in/a"}],
    )

    assert result["contract_version"] == 1
    assert result["status"] == "ok"
    assert result["warnings"] == []
    assert result["error"] is None
    assert result["analyzer"]["platform"] == "generic"
    assert result["analyzer"]["source"] is None
    assert result["columns"] == [{"key": "path", "label": "Path", "type": "string"}]
    assert result["rows"][0]["_row_status"] == "ok"
    assert result["run"]["source_files"] == ["a"]
    assert result["run"]["started_at"] == "2026-01-01T00:00:00Z"


def test_build_result_carries_an_error_on_failure() -> None:
    result = build_result(
        analyzer_id="stub",
        analyzer_name="Stub",
        analyzer_platform="generic",
        analyzer_source=None,
        module_version="1",
        started_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
        duration_ms=1,
        input_path="/tmp/in",
        source_files=[],
        status="error",
        warnings=[],
        error={"message": "boom", "detail": "ValueError"},
        columns=[],
        rows=[],
    )

    assert result["status"] == "error"
    assert result["error"] == {"message": "boom", "detail": "ValueError"}
    assert result["columns"] == []
    assert result["rows"] == []
