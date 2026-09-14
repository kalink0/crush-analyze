"""Loads a LEAPP artifact script — vendored (bundled, curated) or external
(dev mode, an unmodified file a module author has open in an editor) — the
same way in both cases, and adapts each of its `__artifacts_v2__` entries
into crush-analyze's own `ModuleInfo`/`ModuleResult` shape.

A single LEAPP artifact file commonly declares more than one artifact
function (`applicationStateDB.py` declares three), so this returns a list,
not a single module.
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import Any

from . import ilapfuncs
from ..context import Context
from ..contract import Column
from ..module_types import ModuleInfo, ModuleResult

_KNOWN_COLUMN_TYPES = {"string", "int", "float", "bool", "datetime"}


class LeappModuleLoadError(Exception):
    pass


def install_scripts_shim() -> None:
    """Registers `leapp_compat.ilapfuncs` into `sys.modules` under the exact
    dotted name (`scripts.ilapfuncs`) a LEAPP artifact file's own, unmodified
    `from scripts.ilapfuncs import ...` expects — so neither a vendored file
    nor a dev-mode external file needs a real iLEAPP install on the machine
    running crush-analyze. Idempotent; safe to call before every load."""
    if "scripts" not in sys.modules:
        scripts_pkg = ModuleType("scripts")
        scripts_pkg.__path__ = []  # marks it as a package so `scripts.ilapfuncs` resolves
        sys.modules["scripts"] = scripts_pkg
    sys.modules["scripts.ilapfuncs"] = ilapfuncs
    sys.modules["scripts"].ilapfuncs = ilapfuncs  # type: ignore[attr-defined]


def exec_module_file(path: Path) -> ModuleType:
    """Installs the `scripts.ilapfuncs` shim and `exec`s `path` as a fresh
    module object. Shared by `load_leapp_module_file` below and by
    `runner.load_external_module`'s dev-mode path, which needs the raw
    module object first to check for crush-analyze's own native `MODULE`
    convention before falling back to `__artifacts_v2__`."""
    if not path.is_file():
        raise LeappModuleLoadError(f"module file not found: {path}")

    install_scripts_shim()

    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        raise LeappModuleLoadError(f"could not load a module spec from {path}")
    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
    except Exception as exc:
        raise LeappModuleLoadError(f"{path} raised while loading: {exc}") from exc
    return module


def artifacts_from_module(module: ModuleType, path: Path) -> list[ModuleInfo]:
    artifacts = getattr(module, "__artifacts_v2__", None)
    if not artifacts:
        raise LeappModuleLoadError(f"{path} has no __artifacts_v2__ dict")

    infos = []
    for func_name, meta in artifacts.items():
        func = getattr(module, func_name, None)
        if func is None:
            raise LeappModuleLoadError(
                f"{path}: {func_name} is declared in __artifacts_v2__ but not defined"
            )
        infos.append(
            ModuleInfo(
                id=func_name,
                name=meta.get("name", func_name),
                module_version=str(meta.get("last_update_date", "unknown")),
                run=_adapt(func),
                paths=_normalize_paths(meta.get("paths", "*")),
                requires=_normalize_requirements(meta.get("requirements", "none")),
            )
        )
    return infos


def load_leapp_module_file(path: Path) -> list[ModuleInfo]:
    module = exec_module_file(path)
    return artifacts_from_module(module, path)


def _normalize_paths(paths: Any) -> list[str]:
    return [paths] if isinstance(paths, str) else list(paths)


def _normalize_requirements(requirements: Any) -> list[str]:
    return [] if requirements in (None, "none", "") else [str(requirements)]


def _adapt(func: Callable[[Context], tuple[Any, Any, Any]]) -> Callable[[Context], ModuleResult]:
    """Wraps a LEAPP artifact function's own `(context) -> (data_headers,
    data_list, source_path)` return shape into crush-analyze's
    `ModuleResult`. `source_path` is discarded here — contract v1 already
    carries `run.input_path`, and reporting LEAPP's own extraction-relative
    path formatting is `artifact_processor`'s job, not something this
    identity shim reproduces."""

    def run(context: Context) -> ModuleResult:
        data_headers, data_list, _source_path = func(context)
        columns = [_column_from_header(header) for header in data_headers]
        keys = [column.key for column in columns]
        rows = [{"_row_status": "ok", **dict(zip(keys, row, strict=True))} for row in data_list]
        return ModuleResult(columns=columns, rows=rows)

    return run


def _column_from_header(header: Any) -> Column:
    if isinstance(header, tuple):
        label, col_type = header
    else:
        label, col_type = header, "string"
    if col_type not in _KNOWN_COLUMN_TYPES:
        col_type = "string"
    return Column(key=_slugify(label), label=label, type=col_type)


def _slugify(label: str) -> str:
    slug = "".join(c.lower() if c.isalnum() else "_" for c in label)
    while "__" in slug:
        slug = slug.replace("__", "_")
    slug = slug.strip("_")
    return slug or "value"
