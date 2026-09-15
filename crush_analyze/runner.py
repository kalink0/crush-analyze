from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .context import Context, find_files
from .contract import build_result
from .module_types import ModuleInfo


def run(module_info: ModuleInfo, input_path: Path) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    start = time.monotonic()

    files_found = find_files(input_path, module_info.paths)
    context = Context(input_path=input_path, files_found=files_found)

    try:
        result = module_info.run(context)
        status, warnings, columns, rows, error = (
            result.status,
            result.warnings,
            result.columns,
            result.rows,
            None,
        )
    except Exception as exc:  # noqa: BLE001 -- a module's own bug must become an error-status result, never crash the CLI
        status, warnings, columns, rows = "error", [], [], []
        error = {"message": str(exc), "detail": exc.__class__.__name__}

    duration_ms = int((time.monotonic() - start) * 1000)

    return build_result(
        analyzer_id=module_info.id,
        analyzer_name=module_info.name,
        analyzer_platform=module_info.platform,
        analyzer_source=module_info.source.to_dict() if module_info.source else None,
        module_version=module_info.module_version,
        started_at=started_at,
        duration_ms=duration_ms,
        input_path=str(input_path),
        # Relative to input_path, not absolute -- the absolute path only
        # means anything inside this run's own (often temp, since-deleted)
        # extraction directory, matching Context.get_relative_path's own
        # convention for anything shown back to a caller. `as_posix()`, not
        # `str()`: contract v1 is consumed cross-platform (this CLI can run
        # on Windows), and a path in JSON output must not depend on which
        # OS produced it -- str() gives backslashes on Windows, which broke
        # the Windows CI run.
        source_files=[p.relative_to(input_path).as_posix() for p in files_found],
        status=status,
        warnings=warnings,
        error=error,
        columns=columns,
        rows=rows,
    )
