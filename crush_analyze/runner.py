from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .context import Context, find_files
from .contract import build_result
from .leapp_compat import loader as leapp_loader
from .module_types import ModuleInfo


class ModuleLoadError(Exception):
    pass


def load_external_module(path: Path, module_id: str | None = None) -> ModuleInfo:
    """Loads a dev-mode module: an arbitrary, non-vendored `.py` file a
    module author has open in an editor. Nothing about this path trusts the
    file beyond running it — it's still just `exec`-ing Python the caller
    pointed at, same trust model as running any script.

    Two shapes are recognized, tried in this order:

    1. crush-analyze's own native convention — a module-level
       `MODULE = ModuleInfo(...)`, exactly what a bundled module in
       `crush_analyze/modules/` uses.
    2. A LEAPP-shaped artifact file (`__artifacts_v2__` + one or more
       `@artifact_processor`-decorated functions) — the shape a module
       author's real, unmodified iLEAPP source has, which is the actual
       point of dev mode. A file declaring more than one artifact function
       (common — see the vendored `applicationStateDB.py`) requires
       `module_id` to say which one to run.
    """
    try:
        module = leapp_loader.exec_module_file(path)
    except leapp_loader.LeappModuleLoadError as exc:
        raise ModuleLoadError(str(exc)) from exc

    native = getattr(module, "MODULE", None)
    if isinstance(native, ModuleInfo):
        return native

    try:
        infos = leapp_loader.artifacts_from_module(module, path)
    except leapp_loader.LeappModuleLoadError as exc:
        raise ModuleLoadError(str(exc)) from exc

    if module_id:
        for info in infos:
            if info.id == module_id:
                return info
        available = ", ".join(info.id for info in infos)
        raise ModuleLoadError(
            f"{path} has no artifact function {module_id!r} (available: {available})"
        )
    if len(infos) == 1:
        return infos[0]
    available = ", ".join(info.id for info in infos)
    raise ModuleLoadError(
        f"{path} declares {len(infos)} artifact functions ({available}) -- pass --module to pick one"
    )


def run(
    module_info: ModuleInfo,
    input_path: Path,
    *,
    dev_mode: bool,
    module_source: str,
) -> dict[str, Any]:
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
        # convention for anything shown back to a caller.
        source_files=[str(p.relative_to(input_path)) for p in files_found],
        dev_mode=dev_mode,
        module_source=module_source,
        status=status,
        warnings=warnings,
        error=error,
        columns=columns,
        rows=rows,
    )
