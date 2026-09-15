from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from crush_analyze.context import Context
from crush_analyze.leapp_compat import ilapfuncs
from crush_analyze.leapp_compat.loader import LeappModuleLoadError, load_leapp_module_file

_DUMMY_CONTEXT = Context(input_path=Path("."), files_found=[])


def _abx_u16(value: int) -> bytes:
    return value.to_bytes(2, "big")


def _abx_utf(s: str) -> bytes:
    encoded = s.encode("utf-8")
    return _abx_u16(len(encoded)) + encoded


def _abx_interned(s: str) -> bytes:
    return _abx_u16(0xFFFF) + _abx_utf(s)


def _make_abx_bytes() -> bytes:
    """A minimal, synthetic ABX file for: <root attr="value"/> -- same
    construction crush-forensics' own conftest.py/test_parsers.py use for
    testing crush/parsers/abx_decoder.py, since this shim wraps a deliberate
    duplicate of that exact decoder (see leapp_compat/abx_decoder.py)."""
    magic = b"ABX\x00"
    start_tag = bytes([0x22]) + _abx_utf("root")  # TYPE_STRING + START_TAG
    attr = bytes([0x2F]) + _abx_interned("attr") + _abx_utf("value")  # ATTRIBUTE token
    end_tag = bytes([0x23]) + _abx_utf("root")  # TYPE_STRING + END_TAG
    return magic + start_tag + attr + end_tag


def test_get_file_path_matches_a_glob_pattern() -> None:
    files = ["/a/b/applicationState.db", "/a/b/other.db"]

    assert ilapfuncs.get_file_path(files, "applicationState.db*") == "/a/b/applicationState.db"


def test_get_file_path_returns_none_when_nothing_matches() -> None:
    assert ilapfuncs.get_file_path(["/a/b/other.db"], "applicationState.db*") is None


def test_open_sqlite_db_readonly_returns_none_for_a_missing_path() -> None:
    assert ilapfuncs.open_sqlite_db_readonly(None) is None
    assert ilapfuncs.open_sqlite_db_readonly("") is None


def test_open_sqlite_db_readonly_opens_a_real_db(tmp_path: Path) -> None:
    db_path = tmp_path / "x.db"
    sqlite3.connect(db_path).execute("CREATE TABLE t (a INTEGER)")

    conn = ilapfuncs.open_sqlite_db_readonly(str(db_path))

    assert conn is not None
    conn.close()


def test_is_platform_windows_matches_sys_platform() -> None:
    assert ilapfuncs.is_platform_windows() == (sys.platform == "win32")


def test_checkabx_detects_the_magic_header(tmp_path: Path) -> None:
    abx_path = tmp_path / "settings.xml"
    abx_path.write_bytes(_make_abx_bytes())
    plain_path = tmp_path / "plain.xml"
    plain_path.write_text("<root/>")

    assert ilapfuncs.checkabx(str(abx_path)) is True
    assert ilapfuncs.checkabx(str(plain_path)) is False


def test_checkabx_returns_false_for_a_missing_file(tmp_path: Path) -> None:
    assert ilapfuncs.checkabx(str(tmp_path / "missing.xml")) is False


def test_abxread_returns_an_elementtree_with_a_working_getroot(tmp_path: Path) -> None:
    abx_path = tmp_path / "settings.xml"
    abx_path.write_bytes(_make_abx_bytes())

    tree = ilapfuncs.abxread(str(abx_path), False)

    root = tree.getroot()
    assert root is not None
    assert root.tag == "root"
    assert root.attrib["attr"] == "value"


def test_artifact_processor_is_a_pure_pass_through() -> None:
    @ilapfuncs.artifact_processor
    def fn(context: object) -> tuple[str, ...]:
        return ("a", "b")

    assert fn(None) == ("a", "b")


def test_load_leapp_module_file_rejects_a_missing_file(tmp_path: Path) -> None:
    try:
        load_leapp_module_file(tmp_path / "missing.py")
        assert False, "expected LeappModuleLoadError"
    except LeappModuleLoadError:
        pass


def test_load_leapp_module_file_rejects_a_file_without_artifacts_v2(tmp_path: Path) -> None:
    module_file = tmp_path / "plain.py"
    module_file.write_text("x = 1\n")

    try:
        load_leapp_module_file(module_file)
        assert False, "expected LeappModuleLoadError"
    except LeappModuleLoadError:
        pass


def test_load_leapp_module_file_adapts_headers_rows_and_types(tmp_path: Path) -> None:
    module_file = tmp_path / "artifact.py"
    module_file.write_text(
        "__artifacts_v2__ = {\n"
        "    'get_thing': {'name': 'Thing', 'paths': '*.db', 'last_update_date': '2026-01-01'},\n"
        "}\n"
        "from scripts.ilapfuncs import artifact_processor, logfunc\n"
        "@artifact_processor\n"
        "def get_thing(context):\n"
        "    logfunc('hello')\n"
        "    headers = (('When', 'datetime'), 'Name')\n"
        "    return headers, [('2026-01-01T00:00:00Z', 'a')], 'src'\n"
    )

    infos = load_leapp_module_file(module_file)

    assert len(infos) == 1
    info = infos[0]
    assert info.id == "get_thing"
    assert info.name == "Thing"
    assert info.module_version == "2026-01-01"
    assert info.paths == ["*.db"]

    result = info.run(_DUMMY_CONTEXT)
    assert [c.to_dict() for c in result.columns] == [
        {"key": "when", "label": "When", "type": "datetime"},
        {"key": "name", "label": "Name", "type": "string"},
    ]
    assert result.rows == [{"_row_status": "ok", "when": "2026-01-01T00:00:00Z", "name": "a"}]


def test_load_leapp_module_file_falls_back_to_string_type_for_unknown_header_types(
    tmp_path: Path,
) -> None:
    module_file = tmp_path / "artifact.py"
    module_file.write_text(
        "__artifacts_v2__ = {'get_thing': {'name': 'Thing', 'paths': '*.db'}}\n"
        "from scripts.ilapfuncs import artifact_processor\n"
        "@artifact_processor\n"
        "def get_thing(context):\n"
        "    return ((('Odd', 'not-a-real-type'),)), [('x',)], 'src'\n"
    )

    infos = load_leapp_module_file(module_file)

    assert infos[0].run(_DUMMY_CONTEXT).columns[0].type == "string"


def test_load_leapp_module_file_errors_when_a_declared_function_is_missing(tmp_path: Path) -> None:
    module_file = tmp_path / "artifact.py"
    module_file.write_text("__artifacts_v2__ = {'ghost': {'name': 'Ghost'}}\n")

    try:
        load_leapp_module_file(module_file)
        assert False, "expected LeappModuleLoadError"
    except LeappModuleLoadError as exc:
        assert "ghost" in str(exc)
