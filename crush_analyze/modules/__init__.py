from __future__ import annotations

from . import stub
from .base import ModuleInfo

_MODULES: dict[str, ModuleInfo] = {
    stub.MODULE.id: stub.MODULE,
}


class UnknownModuleError(Exception):
    pass


def list_modules() -> list[dict[str, object]]:
    return [
        {
            "id": module.id,
            "name": module.name,
            "module_version": module.module_version,
            "requires": module.requires,
        }
        for module in _MODULES.values()
    ]


def get_module(module_id: str) -> ModuleInfo:
    try:
        return _MODULES[module_id]
    except KeyError:
        raise UnknownModuleError(f"unknown module id: {module_id!r}") from None
