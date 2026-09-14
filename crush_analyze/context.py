"""A minimal, from-scratch reimplementation of the handful of calls a
ported LEAPP artifact module actually makes against its own `Context`
object — not a vendored copy of iLEAPP's real `Context`/`FileSeekerDir`.

See docs/design/analyzer-runner.md in crush-forensics, "Vendoring policy":
those classes are LEAPP's own internal framework plumbing, not a
separately-published reusable library, so they're reimplemented here
rather than copied. Extend this on demand as ported modules turn out to
need more than `get_files_found()`/`get_relative_path()`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Context:
    input_path: Path
    files_found: list[Path] = field(default_factory=list)

    def get_files_found(self) -> list[str]:
        return [str(p) for p in self.files_found]

    def get_relative_path(self, path: str) -> str:
        return str(Path(path).relative_to(self.input_path))


def find_files(input_path: Path, patterns: list[str]) -> list[Path]:
    """Walks `input_path` for every glob `patterns` entry, matching the
    file-discovery step LEAPP's own framework normally performs before
    calling a module — a module here never searches the filesystem itself,
    it only reads back what's already in `Context.files_found`."""
    found: set[Path] = set()
    for pattern in patterns:
        found.update(p for p in input_path.rglob(pattern) if p.is_file())
    return sorted(found)
