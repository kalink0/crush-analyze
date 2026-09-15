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
class SourceInfo:
    """Where a vendored module's own upstream file came from -- read from
    that platform's MANIFEST.toml (see vendored/leapp/*/MANIFEST.toml), not
    something a module author sets. `url` is a commit-pinned link to the
    exact file content this vendored copy was fetched from (a GitHub "blob"
    URL, since every current upstream_repo is a github.com repo), not just a
    link to the repo -- the whole point is showing the exact underlying
    version a result was produced against, not whatever the repo's default
    branch currently has."""

    repo: str
    commit: str
    path: str
    url: str

    def to_dict(self) -> dict[str, str]:
        return {"repo": self.repo, "commit": self.commit, "path": self.path, "url": self.url}


@dataclass
class ModuleInfo:
    """`platform` is "ios" | "android" for a vendored LEAPP-family module,
    set from its vendored/leapp/<platform>/ subdirectory -- "generic" for a
    platform-agnostic module (e.g. the stub).

    `source` is None for the stub module (there is no upstream commit to
    pin to)."""

    id: str
    name: str
    module_version: str
    run: Callable[[Context], ModuleResult]
    paths: list[str] = field(default_factory=lambda: ["*"])
    requires: list[str] = field(default_factory=list)
    platform: str = "generic"
    source: SourceInfo | None = None
