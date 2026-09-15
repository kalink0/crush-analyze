from __future__ import annotations

from pathlib import Path

from crush_analyze.modules import get_module
from crush_analyze.runner import ModuleLoadError, load_external_module, run
from crush_analyze.module_types import ModuleInfo, ModuleResult


def test_run_stub_module_returns_ok_status(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")

    result = run(get_module("stub"), tmp_path, dev_mode=False, module_source="bundled")

    assert result["status"] == "ok"
    assert result["analyzer"]["platform"] == "generic"
    assert result["analyzer"]["source"] is None
    assert result["rows"] == [{"_row_status": "ok", "path": str(tmp_path / "a.txt")}]


def test_run_catches_an_exception_from_the_module_as_error_status(tmp_path: Path) -> None:
    def broken_run(context: object) -> ModuleResult:
        raise ValueError("boom")

    broken = ModuleInfo(id="broken", name="Broken", module_version="1", run=broken_run)

    result = run(broken, tmp_path, dev_mode=False, module_source="bundled")

    assert result["status"] == "error"
    assert result["error"] == {"message": "boom", "detail": "ValueError"}
    assert result["rows"] == []


def test_load_external_module_reads_a_module_level_module_constant(tmp_path: Path) -> None:
    module_file = tmp_path / "my_module.py"
    module_file.write_text(
        "from crush_analyze.module_types import ModuleInfo, ModuleResult\n"
        "from crush_analyze.contract import Column\n"
        "\n"
        "def run(context):\n"
        "    return ModuleResult(columns=[Column('x', 'X', 'string')], rows=[])\n"
        "\n"
        "MODULE = ModuleInfo(id='my_module', name='My Module', module_version='1', run=run)\n"
    )

    info = load_external_module(module_file)

    assert info.id == "my_module"


def test_load_external_module_rejects_a_missing_file(tmp_path: Path) -> None:
    try:
        load_external_module(tmp_path / "missing.py")
        assert False, "expected ModuleLoadError"
    except ModuleLoadError:
        pass


def test_load_external_module_rejects_a_file_without_module_constant(tmp_path: Path) -> None:
    module_file = tmp_path / "no_module.py"
    module_file.write_text("x = 1\n")

    try:
        load_external_module(module_file)
        assert False, "expected ModuleLoadError"
    except ModuleLoadError:
        pass


_LEAPP_TWO_ARTIFACT_FILE = '''
__artifacts_v2__ = {
    "first_artifact": {"name": "First", "paths": "*.txt"},
    "second_artifact": {"name": "Second", "paths": "*.txt"},
}

from scripts.ilapfuncs import artifact_processor


@artifact_processor
def first_artifact(context):
    return ("Value",), [("a",)], "src"


@artifact_processor
def second_artifact(context):
    return ("Value",), [("b",)], "src"
'''


def test_load_external_module_requires_module_id_when_a_leapp_file_has_several(
    tmp_path: Path,
) -> None:
    module_file = tmp_path / "two_artifacts.py"
    module_file.write_text(_LEAPP_TWO_ARTIFACT_FILE)

    try:
        load_external_module(module_file)
        assert False, "expected ModuleLoadError"
    except ModuleLoadError as exc:
        assert "first_artifact" in str(exc)
        assert "second_artifact" in str(exc)


def test_load_external_module_picks_the_requested_leapp_artifact(tmp_path: Path) -> None:
    module_file = tmp_path / "two_artifacts.py"
    module_file.write_text(_LEAPP_TWO_ARTIFACT_FILE)

    info = load_external_module(module_file, module_id="second_artifact")

    assert info.id == "second_artifact"
    assert info.name == "Second"


def test_load_external_module_rejects_an_unknown_module_id(tmp_path: Path) -> None:
    module_file = tmp_path / "two_artifacts.py"
    module_file.write_text(_LEAPP_TWO_ARTIFACT_FILE)

    try:
        load_external_module(module_file, module_id="nope")
        assert False, "expected ModuleLoadError"
    except ModuleLoadError as exc:
        assert "nope" in str(exc)


def test_run_real_vendored_installed_apps_module_against_a_synthetic_fixture(
    tmp_path: Path,
) -> None:
    import plistlib
    import sqlite3

    db_path = tmp_path / "private" / "var" / "mobile" / "Library" / "FrontBoard" / "applicationState.db"
    db_path.parent.mkdir(parents=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE application_identifier_tab (id INTEGER PRIMARY KEY, application_identifier TEXT)"
    )
    conn.execute("CREATE TABLE key_tab (id INTEGER PRIMARY KEY, key TEXT)")
    conn.execute("CREATE TABLE kvs (application_identifier INTEGER, key INTEGER, value BLOB)")
    conn.execute("INSERT INTO application_identifier_tab VALUES (1, 'app1')")
    conn.execute("INSERT INTO key_tab VALUES (1, 'compatibilityInfo')")
    compat_plist = plistlib.dumps(
        {
            "bundleIdentifier": "com.example.testapp",
            "bundlePath": "/private/var/containers/Bundle/Application/XXXX/TestApp.app",
            "sandboxPath": "/private/var/mobile/Containers/Data/Application/XXXX",
        },
        fmt=plistlib.FMT_BINARY,
    )
    conn.execute("INSERT INTO kvs VALUES (1, 1, ?)", (compat_plist,))
    conn.commit()
    conn.close()

    result = run(get_module("get_installed_apps"), tmp_path, dev_mode=False, module_source="bundled")

    assert result["status"] == "ok"
    assert result["analyzer"]["platform"] == "ios"
    assert result["analyzer"]["source"] == {
        "repo": "https://github.com/abrignoni/iLEAPP",
        "commit": "b055398e485daae838ba3c55fd611cc303f0a854",
        "path": "scripts/artifacts/applicationStateDB.py",
        "url": "https://github.com/abrignoni/iLEAPP/blob/"
        "b055398e485daae838ba3c55fd611cc303f0a854/scripts/artifacts/applicationStateDB.py",
    }
    assert result["rows"] == [
        {
            "_row_status": "ok",
            "bundle_id": "com.example.testapp",
            "bundle_path": "/private/var/containers/Bundle/Application/XXXX/TestApp.app",
            "sandbox_path": "/private/var/mobile/Containers/Data/Application/XXXX",
        }
    ]


def test_run_real_vendored_installedapps_vending_module_against_a_synthetic_fixture(
    tmp_path: Path,
) -> None:
    import sqlite3
    from datetime import datetime, timezone

    db_path = tmp_path / "data" / "data" / "com.android.vending" / "databases" / "localappstate.db"
    db_path.parent.mkdir(parents=True)
    conn = sqlite3.connect(db_path)
    conn.execute(
        "CREATE TABLE appstate ("
        "first_download_ms INTEGER, package_name TEXT, title TEXT, install_reason TEXT, "
        "last_update_timestamp_ms INTEGER, auto_update TEXT, account TEXT)"
    )
    conn.execute(
        "INSERT INTO appstate VALUES "
        "(1735689600000, 'com.example.testapp', 'Test App', '0', "
        "1735776000000, '1', 'user@example.com')"
    )
    conn.commit()
    conn.close()

    result = run(
        get_module("get_installedappsVending"), tmp_path, dev_mode=False, module_source="bundled"
    )

    assert result["status"] == "ok"
    assert result["analyzer"]["platform"] == "android"
    assert result["analyzer"]["source"] == {
        "repo": "https://github.com/abrignoni/aLEAPP",
        "commit": "bdc6a5bd841910ef7e7cc71ed4f57b8fc4122306",
        "path": "scripts/artifacts/installedappsVending.py",
        "url": "https://github.com/abrignoni/aLEAPP/blob/"
        "bdc6a5bd841910ef7e7cc71ed4f57b8fc4122306/scripts/artifacts/installedappsVending.py",
    }
    assert result["rows"] == [
        {
            "_row_status": "ok",
            "user": "0",
            "first_download": datetime(2025, 1, 1, tzinfo=timezone.utc),
            "package_name": "com.example.testapp",
            "title": "Test App",
            "install_reason": "0",
            "last_updated": datetime(2025, 1, 2, tzinfo=timezone.utc),
            "auto_update": "Yes",
            "account": "user@example.com",
        }
    ]
