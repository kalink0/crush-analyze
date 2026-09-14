"""Builds the result contract v1 JSON — see docs/design/analyzer-runner.md
in crush-forensics for the frozen field-by-field spec. `status`,
`warnings`, `error` and each row's `_row_status` are mandatory, not
optional-with-defaults: a failed or partial run must never render as a
clean, empty-looking table, and one bad row must never silently drop or
fail the whole run.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from . import __version__

CONTRACT_VERSION = 1


@dataclass
class Column:
    key: str
    label: str
    type: str  # "string" | "int" | "float" | "bool" | "datetime"

    def to_dict(self) -> dict[str, str]:
        return {"key": self.key, "label": self.label, "type": self.type}


def build_result(
    *,
    analyzer_id: str,
    analyzer_name: str,
    module_version: str,
    started_at: datetime,
    duration_ms: int,
    input_path: str,
    dev_mode: bool,
    module_source: str,
    status: str,
    warnings: list[str],
    error: dict[str, str] | None,
    columns: list[Column],
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "contract_version": CONTRACT_VERSION,
        "analyzer": {
            "id": analyzer_id,
            "name": analyzer_name,
            "tool": "crush-analyze",
            "tool_version": __version__,
            "module_version": module_version,
        },
        "run": {
            "started_at": started_at.isoformat().replace("+00:00", "Z"),
            "duration_ms": duration_ms,
            "input_path": input_path,
            "dev_mode": dev_mode,
            "module_source": module_source,
        },
        "status": status,
        "warnings": warnings,
        "error": error,
        "columns": [c.to_dict() for c in columns],
        "rows": rows,
    }
