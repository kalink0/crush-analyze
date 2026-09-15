from __future__ import annotations

from pathlib import Path

from crush_analyze.modules import get_module
from crush_analyze.runner import run
from crush_analyze.module_types import ModuleInfo, ModuleResult


def test_run_stub_module_returns_ok_status(tmp_path: Path) -> None:
    (tmp_path / "a.txt").write_text("x")

    result = run(get_module("stub"), tmp_path)

    assert result["status"] == "ok"
    assert result["analyzer"]["platform"] == "generic"
    assert result["analyzer"]["source"] is None
    assert result["run"]["source_files"] == ["a.txt"]
    assert result["rows"] == [{"_row_status": "ok", "path": str(tmp_path / "a.txt")}]


def test_run_catches_an_exception_from_the_module_as_error_status(tmp_path: Path) -> None:
    def broken_run(context: object) -> ModuleResult:
        raise ValueError("boom")

    broken = ModuleInfo(id="broken", name="Broken", module_version="1", run=broken_run)

    result = run(broken, tmp_path)

    assert result["status"] == "error"
    assert result["error"] == {"message": "boom", "detail": "ValueError"}
    assert result["rows"] == []


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

    result = run(get_module("get_installed_apps"), tmp_path)

    assert result["status"] == "ok"
    assert result["analyzer"]["platform"] == "ios"
    assert result["analyzer"]["source"] == {
        "repo": "https://github.com/abrignoni/iLEAPP",
        "commit": "b055398e485daae838ba3c55fd611cc303f0a854",
        "path": "scripts/artifacts/applicationStateDB.py",
        "url": "https://github.com/abrignoni/iLEAPP/blob/"
        "b055398e485daae838ba3c55fd611cc303f0a854/scripts/artifacts/applicationStateDB.py",
    }
    assert result["run"]["source_files"] == [
        "private/var/mobile/Library/FrontBoard/applicationState.db"
    ]
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

    result = run(get_module("get_installedappsVending"), tmp_path)

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


def test_run_real_vendored_package_info_module_against_a_plain_xml_fixture(tmp_path: Path) -> None:
    """The plain-XML branch (checkabx returns False on a real packages.xml
    header, module falls back to plain xmltodict.parse). Real Android
    packages.xml stores its timestamp attributes as hex-digit strings
    (fed through Python's float.fromhex by the vendored module's own
    ReadUnixTimeMs) -- not plain decimal, which would silently produce a
    wildly wrong date instead of failing loudly."""
    pkg_path = tmp_path / "data" / "system" / "packages.xml"
    pkg_path.parent.mkdir(parents=True)
    pkg_path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<packages>\n"
        '  <package name="com.example.testapp" ft="0" it="18bcfe56800" ut="18bcfe6f680" '
        'installOriginator="com.android.vending" installer="com.android.vending" '
        'codePath="/data/app/com.example.testapp" publicFlags="1" privateFlags="0"/>\n'
        '  <package name="com.example.secondapp" ft="0" it="174876e8000" ut="174876ff880" '
        'installOriginator="com.android.vending" installer="com.android.vending" '
        'codePath="/data/app/com.example.secondapp" publicFlags="1" privateFlags="0"/>\n'
        "</packages>\n"
    )

    result = run(get_module("get_package_info"), tmp_path)

    assert result["status"] == "ok"
    assert result["analyzer"]["platform"] == "android"
    assert result["analyzer"]["source"] == {
        "repo": "https://github.com/abrignoni/aLEAPP",
        "commit": "3abea7d798a1687fcb31afa84a6030f85ad65539",
        "path": "scripts/artifacts/packageInfo.py",
        "url": "https://github.com/abrignoni/aLEAPP/blob/"
        "3abea7d798a1687fcb31afa84a6030f85ad65539/scripts/artifacts/packageInfo.py",
    }
    from datetime import datetime, timezone

    assert result["rows"] == [
        {
            "_row_status": "ok",
            "ft": datetime(1970, 1, 1, tzinfo=timezone.utc),
            "name": "com.example.testapp",
            "install_time": datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc),
            "update_time": datetime(2023, 11, 14, 22, 15, 2, 16000, tzinfo=timezone.utc),
            "install_originator": "com.android.vending",
            "installer": "com.android.vending",
            "code_path": "/data/app/com.example.testapp",
            "public_flags": "0x1",
            "private_flags": "0x0",
        },
        {
            "_row_status": "ok",
            "ft": datetime(1970, 1, 1, tzinfo=timezone.utc),
            "name": "com.example.secondapp",
            "install_time": datetime(2020, 9, 13, 12, 26, 40, tzinfo=timezone.utc),
            "update_time": datetime(2020, 9, 13, 12, 28, 16, 384000, tzinfo=timezone.utc),
            "install_originator": "com.android.vending",
            "installer": "com.android.vending",
            "code_path": "/data/app/com.example.secondapp",
            "public_flags": "0x1",
            "private_flags": "0x0",
        },
    ]


def test_run_real_vendored_package_info_module_against_an_abx_fixture(tmp_path: Path) -> None:
    """The ABX branch (checkabx returns True), exercising the shim's
    abxread()/checkabx() -- not just the plain-XML fallback above. Two
    <package> elements, not one: xmltodict.parse only returns a *list*
    for a repeated element -- a single one comes back as a bare dict,
    which the vendored module's own `for package in package_dict:` would
    then iterate as dict *keys* instead of package records. Matches the
    same reasoning in the plain-XML fixture test above."""
    from tests.test_leapp_compat import _abx_interned, _abx_utf

    def _abx_attr(name: str, value: str) -> bytes:
        return bytes([0x2F]) + _abx_interned(name) + _abx_utf(value)  # ATTRIBUTE, TYPE_STRING

    def _abx_package(name: str, code_path: str) -> bytes:
        start = bytes([0x22]) + _abx_utf("package")  # TYPE_STRING + START_TAG
        attrs = (
            _abx_attr("name", name)
            + _abx_attr("ft", "0")
            + _abx_attr("it", "18bcfe56800")
            + _abx_attr("ut", "18bcfe6f680")
            + _abx_attr("installOriginator", "com.android.vending")
            + _abx_attr("installer", "com.android.vending")
            + _abx_attr("codePath", code_path)
            + _abx_attr("publicFlags", "1")
            + _abx_attr("privateFlags", "0")
        )
        end = bytes([0x23]) + _abx_utf("package")  # TYPE_STRING + END_TAG
        return start + attrs + end

    magic = b"ABX\x00"
    packages_start = bytes([0x22]) + _abx_utf("packages")
    packages_end = bytes([0x23]) + _abx_utf("packages")
    abx_bytes = (
        magic
        + packages_start
        + _abx_package("com.example.testapp", "/data/app/com.example.testapp")
        + _abx_package("com.example.secondapp", "/data/app/com.example.secondapp")
        + packages_end
    )

    pkg_path = tmp_path / "data" / "system" / "packages.xml"
    pkg_path.parent.mkdir(parents=True)
    pkg_path.write_bytes(abx_bytes)

    result = run(get_module("get_package_info"), tmp_path)

    assert result["status"] == "ok"
    assert len(result["rows"]) == 2
    assert result["rows"][0]["name"] == "com.example.testapp"
    assert result["rows"][0]["code_path"] == "/data/app/com.example.testapp"
    assert result["rows"][1]["name"] == "com.example.secondapp"
