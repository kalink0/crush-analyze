"""Fixed, tiny bundled module — proves the CLI/contract/viewer plumbing
end to end before any real module is ported. See docs/design/analyzer-
runner.md in crush-forensics, rollout step 2."""

from __future__ import annotations

from ..context import Context
from ..contract import Column
from .base import ModuleInfo, ModuleResult


def run(context: Context) -> ModuleResult:
    return ModuleResult(
        columns=[Column(key="path", label="Path", type="string")],
        rows=[{"_row_status": "ok", "path": p} for p in context.get_files_found()],
    )


MODULE = ModuleInfo(
    id="stub",
    name="Stub",
    module_version="1",
    run=run,
    paths=["*"],
)
