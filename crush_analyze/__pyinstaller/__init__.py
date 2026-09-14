"""PyInstaller hook auto-discovery entry point (registered under the
`pyinstaller40` entry-point group in pyproject.toml). Any PyInstaller build
that has crush-analyze installed picks this up automatically — no
--add-data entry or knowledge of crush-analyze's internal layout needed on
the caller's side."""

import os


def get_hook_dirs() -> list[str]:
    return [os.path.dirname(__file__)]
