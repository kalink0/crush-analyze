from __future__ import annotations

import sys
from pathlib import Path

from . import stub
from ..leapp_compat.loader import LeappModuleLoadError, load_leapp_module_file
from ..module_types import ModuleInfo

_VENDORED_LEAPP_DIR = Path(__file__).resolve().parent.parent / "vendored" / "leapp"


class UnknownModuleError(Exception):
    pass


def _load_vendored_modules() -> list[ModuleInfo]:
    """Loads every vendored LEAPP artifact file under vendored/leapp/. A
    file that fails to load (e.g. a missing optional third-party
    dependency for one specific module) is skipped with a warning rather
    than aborting the whole CLI — matches LEAPP's own "a module can
    disable itself" behavior, and means `list-modules` still reports
    everything that *is* usable."""
    infos: list[ModuleInfo] = []
    if not _VENDORED_LEAPP_DIR.is_dir():
        return infos
    for path in sorted(_VENDORED_LEAPP_DIR.glob("*.py")):
        try:
            infos.extend(load_leapp_module_file(path))
        except LeappModuleLoadError as exc:
            print(f"warning: could not load vendored module {path.name}: {exc}", file=sys.stderr)
    return infos


_MODULES: dict[str, ModuleInfo] = {stub.MODULE.id: stub.MODULE}
for _info in _load_vendored_modules():
    _MODULES[_info.id] = _info


def list_modules() -> list[dict[str, object]]:
    return [
        {
            "id": module.id,
            "name": module.name,
            "module_version": module.module_version,
            "requires": module.requires,
            "paths": module.paths,
        }
        for module in _MODULES.values()
    ]


def get_module(module_id: str) -> ModuleInfo:
    try:
        return _MODULES[module_id]
    except KeyError:
        raise UnknownModuleError(f"unknown module id: {module_id!r}") from None
