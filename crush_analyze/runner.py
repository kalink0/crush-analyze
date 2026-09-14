from __future__ import annotations

import importlib.util
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .context import Context, find_files
from .contract import build_result
from .modules.base import ModuleInfo


class ModuleLoadError(Exception):
    pass


def load_external_module(path: Path) -> ModuleInfo:
    """Loads a dev-mode module: an arbitrary, non-vendored `.py` file
    exposing a module-level `MODULE = ModuleInfo(...)`, exactly the same
    shape a bundled module in `crush_analyze/modules/` uses. Nothing about
    this path trusts the file beyond that — it's still just `exec`-ing
    Python the caller pointed at, same trust model as running any script."""
    if not path.is_file():
        raise ModuleLoadError(f"module file not found: {path}")
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise ModuleLoadError(f"could not load a module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise ModuleLoadError(f"{path} raised while loading: {exc}") from exc
    info = getattr(module, "MODULE", None)
    if not isinstance(info, ModuleInfo):
        raise ModuleLoadError(f"{path} has no module-level MODULE = ModuleInfo(...)")
    return info


def run(
    module_info: ModuleInfo,
    input_path: Path,
    *,
    dev_mode: bool,
    module_source: str,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    start = time.monotonic()

    context = Context(input_path=input_path, files_found=find_files(input_path, module_info.paths))

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
        module_version=module_info.module_version,
        started_at=started_at,
        duration_ms=duration_ms,
        input_path=str(input_path),
        dev_mode=dev_mode,
        module_source=module_source,
        status=status,
        warnings=warnings,
        error=error,
        columns=columns,
        rows=rows,
    )
