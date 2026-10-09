from __future__ import annotations

import importlib.util

from crush_analyze.__pyinstaller import vendored_imports


def test_vendored_imports_lists_third_party_modules() -> None:
    names = vendored_imports()

    assert "xmltodict" in names
    assert "biplist" in names


def test_vendored_imports_skips_stdlib_and_scripts_shim() -> None:
    names = vendored_imports()

    assert not any(name.partition(".")[0] in {"os", "plistlib", "xml", "scripts"} for name in names)


def test_vendored_imports_are_installed() -> None:
    # A vendored file importing something that isn't a declared dependency
    # would load in neither a pip install nor a frozen build.
    missing = [name for name in vendored_imports() if importlib.util.find_spec(name) is None]

    assert missing == []
