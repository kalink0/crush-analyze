"""A minimal, from-scratch reimplementation of the handful of
`scripts.ilapfuncs` symbols a ported/dev-mode LEAPP artifact module
actually imports at its top: `open_sqlite_db_readonly`, `artifact_processor`,
`logfunc`, `get_file_path`, `does_column_exist_in_db`. Not a vendored copy of
iLEAPP's/aLEAPP's real `scripts/ilapfuncs.py` (1900+ lines covering HTML/TSV/
KML/LAVA report generation, GUI log redirection, Windows extended-path
handling for LEAPP's own extraction scheme — none of which crush-analyze
needs or wants to depend on). See docs/design/analyzer-runner.md in
crush-forensics, "Vendoring policy".

Registered into `sys.modules` by `leapp_compat.loader` before a vendored or
external module file is loaded, so that file's own unmodified
`from scripts.ilapfuncs import ...` resolves against this module.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from functools import wraps
from pathlib import Path
from typing import Any


def logfunc(message: str = "") -> None:
    print(message)


def get_file_path(files_found: list[str], filename: str, skip: str | None = None) -> str | None:
    """Returns the first entry in `files_found` whose final path component
    matches the `filename` glob pattern, or `None`. Mirrors iLEAPP's own
    `get_file_path` (`Path(file_found).match(filename)` per candidate)."""
    try:
        for file_found in files_found:
            if skip and skip in file_found:
                continue
            if Path(file_found).match(filename):
                return file_found
    except (OSError, ValueError) as exc:
        logfunc(f"Error: {exc}")
    return None


def open_sqlite_db_readonly(path: str | None) -> sqlite3.Connection | None:
    """Opens a SQLite DB read-only (original file and any -wal/-journal
    stay untouched), or `None` on any failure."""
    if not path:
        return None
    try:
        return sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    except sqlite3.OperationalError as exc:
        logfunc(f"Error with {path}:")
        logfunc(f" - {exc}")
        return None


def does_column_exist_in_db(path: str, table_name: str, col_name: str) -> bool:
    """Checks whether `table_name` has a column named `col_name`, for a
    module reading a table whose schema varies across OS versions. Mirrors
    iLEAPP/aLEAPP's own `does_column_exist_in_db` (`PRAGMA table_info`,
    case-insensitive column-name match)."""
    db = open_sqlite_db_readonly(path)
    if db is None:
        return False
    try:
        cursor = db.cursor()
        cursor.execute(f"pragma table_info('{table_name}')")
        return any(row[1].lower() == col_name.lower() for row in cursor.fetchall())
    finally:
        db.close()


def artifact_processor(func: Callable[..., Any]) -> Callable[..., Any]:
    """iLEAPP's real decorator drives HTML/TSV/KML/LAVA report generation
    around the wrapped function's return value — all of that is Crush's
    own report machinery, which crush-analyze never runs. This is an
    identity pass-through: the wrapped `func(context) -> (data_headers,
    data_list, source_path)` is called and returned unchanged, and
    `leapp_compat.loader` builds crush-analyze's own contract v1 result
    directly from that tuple."""

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    return wrapper
