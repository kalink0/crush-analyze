from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .context import Context
from .contract import Column


@dataclass
class ModuleResult:
    """What a module's own `run(context)` returns. `status` here is only
    ever "ok" or "partial" — an exception raised by the module is what
    produces a contract-level "error" status, caught by the runner, never
    something a module sets itself."""

    columns: list[Column]
    rows: list[dict[str, Any]]
    warnings: list[str] = field(default_factory=list)
    status: str = "ok"


@dataclass
class ModuleInfo:
    id: str
    name: str
    module_version: str
    run: Callable[[Context], ModuleResult]
    paths: list[str] = field(default_factory=lambda: ["*"])
    requires: list[str] = field(default_factory=list)
