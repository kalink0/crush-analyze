"""PyInstaller hook auto-discovery entry point (registered under the
`pyinstaller40` entry-point group in pyproject.toml). Any PyInstaller build
that has crush-analyze installed picks this up automatically — no
--add-data entry or knowledge of crush-analyze's internal layout needed on
the caller's side.

Kept free of PyInstaller imports so `vendored_imports` can be tested
without PyInstaller installed."""

import ast
import os
import sys
from pathlib import Path

_VENDORED_DIR = Path(__file__).resolve().parent.parent / "vendored"

# Provided at runtime by leapp_compat.loader.install_scripts_shim, never by
# a real package.
_SHIM_PACKAGE = "scripts"


def get_hook_dirs() -> list[str]:
    return [os.path.dirname(__file__)]


def vendored_imports() -> list[str]:
    """Every absolute, non-stdlib, non-shim module a vendored file under
    vendored/ imports. The vendored files are loaded by path at runtime
    (leapp_compat.loader), so PyInstaller's import analysis never sees them
    or their imports -- the hook passes this list as `hiddenimports`."""
    names: set[str] = set()
    for path in sorted(_VENDORED_DIR.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.add(node.module)
    return sorted(
        name
        for name in names
        if (top := name.partition(".")[0]) not in sys.stdlib_module_names
        and top != _SHIM_PACKAGE
    )
