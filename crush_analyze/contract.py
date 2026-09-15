"""Builds the result contract v1 JSON — see docs/design/analyzer-runner.md
in crush-forensics for the frozen field-by-field spec. `status`,
`warnings`, `error` and each row's `_row_status` are mandatory, not
optional-with-defaults: a failed or partial run must never render as a
clean, empty-looking table, and one bad row must never silently drop or
fail the whole run.

Additions on top of that frozen spec, made once Android modules joined the
iOS ones: `analyzer.platform` ("ios" | "android" | "generic"), so a
consumer can tell which OS a result's module targets without parsing its
`analyzer.id`; and `analyzer.source` (`null` for the stub module, else
`{repo, commit, path, url}` naming the exact upstream commit a curated
module's vendored copy was fetched from).

One more addition, made for the same reason Crush's Properties panel
wanted `analyzer.source` -- knowing what a result is actually based on:
`run.source_files`, every file (relative to `input_path`) that matched
the module's own declared `paths` glob and was therefore available to it
via `Context.get_files_found()`. This is what the module *had access to*,
not necessarily proof of exactly which bytes it read from each one --
matches "what data is this result based on" the same way `analyzer.source`
answers "what code is this result based on".

All purely additive -- no existing field changed -- but still worth
folding back into the frozen spec doc in crush-forensics, the same way
that doc already tracks other corrections discovered while porting.
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
    analyzer_platform: str,
    analyzer_source: dict[str, str] | None,
    module_version: str,
    started_at: datetime,
    duration_ms: int,
    input_path: str,
    source_files: list[str],
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
            "platform": analyzer_platform,
            "source": analyzer_source,
            "tool": "crush-analyze",
            "tool_version": __version__,
            "module_version": module_version,
        },
        "run": {
            "started_at": started_at.isoformat().replace("+00:00", "Z"),
            "duration_ms": duration_ms,
            "input_path": input_path,
            "source_files": source_files,
        },
        "status": status,
        "warnings": warnings,
        "error": error,
        "columns": [c.to_dict() for c in columns],
        "rows": rows,
    }
