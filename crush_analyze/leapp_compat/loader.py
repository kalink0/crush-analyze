"""Loads a vendored, curated LEAPP artifact script and adapts each of its
`__artifacts_v2__` entries into crush-analyze's own `ModuleInfo`/
`ModuleResult` shape.

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
from ..module_types import ModuleInfo, ModuleResult, SourceInfo

_KNOWN_COLUMN_TYPES = {"string", "int", "float", "bool", "datetime"}


class LeappModuleLoadError(Exception):
    pass


def install_scripts_shim() -> None:
    """Registers `leapp_compat.ilapfuncs` into `sys.modules` under the exact
    dotted name (`scripts.ilapfuncs`) a vendored LEAPP artifact file's own,
    unmodified `from scripts.ilapfuncs import ...` expects — so it needs no
    real iLEAPP/aLEAPP install on the machine running crush-analyze. Also
    registers the vendored
    `scripts.artifacts.storagePathViews` helper a real aLEAPP artifact file
    can import the same way -- unconditionally, exactly like `ilapfuncs`,
    regardless of whether the file being loaded actually needs it.
    Idempotent; safe to call before every load."""
    if "scripts" not in sys.modules:
        scripts_pkg = ModuleType("scripts")
        scripts_pkg.__path__ = []  # marks it as a package so `scripts.ilapfuncs` resolves
        sys.modules["scripts"] = scripts_pkg
    sys.modules["scripts.ilapfuncs"] = ilapfuncs
    sys.modules["scripts"].ilapfuncs = ilapfuncs  # type: ignore[attr-defined]

    if "scripts.artifacts" not in sys.modules:
        artifacts_pkg = ModuleType("scripts.artifacts")
        artifacts_pkg.__path__ = []
        sys.modules["scripts.artifacts"] = artifacts_pkg
        sys.modules["scripts"].artifacts = artifacts_pkg  # type: ignore[attr-defined]
    storage_path_views = _load_android_storage_path_views()
    sys.modules["scripts.artifacts.storagePathViews"] = storage_path_views
    sys.modules["scripts.artifacts"].storagePathViews = storage_path_views  # type: ignore[attr-defined]


def exec_module_file(path: Path, *, install_shim: bool = True) -> ModuleType:
    """Installs the `scripts.ilapfuncs`/`scripts.artifacts.storagePathViews`
    shim and `exec`s `path` as a fresh module object. Shared by
    `load_leapp_module_file` below and by `_load_android_storage_path_views`,
    which needs the raw module object to load a non-artifact helper file.

    `install_shim=False` is for `_load_android_storage_path_views` below only
    -- it loads the shim's own `storagePathViews.py` helper, which imports
    nothing from `scripts.*` and would otherwise recurse straight back into
    `install_scripts_shim`."""
    if not path.is_file():
        raise LeappModuleLoadError(f"module file not found: {path}")

    if install_shim:
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


_ANDROID_HELPER_DIR = Path(__file__).resolve().parent.parent / "vendored" / "leapp" / "android" / "_helpers"
_android_storage_path_views: ModuleType | None = None


def _load_android_storage_path_views() -> ModuleType:
    """Lazily loads and caches the vendored `storagePathViews.py` helper (see
    its entry in vendored/leapp/android/MANIFEST.toml for why this one
    non-artifact file is vendored alongside the android artifact scripts).
    Lives in an `_helpers/` subdirectory precisely so `modules._load_vendored_
    modules`'s `platform_dir.glob("*.py")` never tries to load it as an
    artifact module itself -- it has no `__artifacts_v2__`, which would
    otherwise print a spurious "could not load" warning on every run."""
    global _android_storage_path_views
    if _android_storage_path_views is None:
        _android_storage_path_views = exec_module_file(
            _ANDROID_HELPER_DIR / "storagePathViews.py", install_shim=False
        )
    return _android_storage_path_views


def artifacts_from_module(
    module: ModuleType, path: Path, *, platform: str = "generic", source: SourceInfo | None = None
) -> list[ModuleInfo]:
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
                platform=platform,
                source=source,
            )
        )
    return infos


def load_leapp_module_file(
    path: Path, *, platform: str = "generic", source: SourceInfo | None = None
) -> list[ModuleInfo]:
    module = exec_module_file(path)
    return artifacts_from_module(module, path, platform=platform, source=source)


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
