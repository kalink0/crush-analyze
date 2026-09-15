# Porting LEAPP modules into crush-analyze

A guide for going from an unmodified iLEAPP/aLEAPP/rLEAPP artifact script to
a curated, vendored module in `crush_analyze/vendored/leapp/`. Based on the
actual ports of `applicationStateDB.py` (iOS, see
`crush_analyze/vendored/leapp/ios/MANIFEST.toml` and
`crush_analyze/leapp_compat/`) and `installedappsVending.py` (Android, see
`crush_analyze/vendored/leapp/android/MANIFEST.toml`), and on the "Vendoring
policy" in
[`docs/design/analyzer-runner.md`](https://github.com/kalink0/crush-forensics/blob/main/docs/design/analyzer-runner.md)
(crush-forensics).

## 0. First check: is vendoring even worth it?

Not every LEAPP module needs this machinery. Rule of thumb from the design
doc:

- **Yes, vendor it**, when the script has real complexity you don't want to
  rewrite — SQLite queries, nested/binary plists, multiple artifact
  functions per file, third-party deps (`applicationStateDB.py`: SQLite +
  `biplist`/`nska_deserialize` for NSKeyedArchiver blobs).
- **No, write a native crush-analyze parser instead** (the `MODULE =
  ModuleInfo(...)` convention used by `modules/stub.py`), when the script is
  trivial — the design doc explicitly names `appItunesmeta.py` as an example
  too simple to justify the vendoring overhead.

See also [`docs/module-candidates.md`](./module-candidates.md) for a
concrete list checked against the real iLEAPP/aLEAPP catalog.

## 1. Check the source module for compatibility

Before copying anything, check the original file from iLEAPP/aLEAPP:

1. **Signature version.** Only **v2** is supported: every function in
   `__artifacts_v2__` has the shape `func(context) -> (data_headers,
   data_list, source_path)`. The older v1 shape (`func(files_found,
   report_folder, seeker, wrap_text, timezone_offset)`, 5 positional args)
   is not loaded — `leapp_compat.loader` only understands the
   `__artifacts_v2__` dict.
2. **Imports at the top of the file.** A real artifact script typically
   does `from scripts.ilapfuncs import ...`. The compat shim
   (`crush_analyze/leapp_compat/ilapfuncs.py`) currently covers exactly five
   symbols: `open_sqlite_db_readonly`, `artifact_processor`, `logfunc`,
   `get_file_path`, `does_column_exist_in_db`. If the target module imports
   other `scripts.ilapfuncs` symbols (e.g. `convert_ts_human_to_utc`,
   `get_plist_content`, `abxread`/`checkabx`), those need to be
   **minimally reimplemented** there — never vendor the real, 1900-line
   `ilapfuncs.py` from iLEAPP/aLEAPP (see "Vendoring policy" in the design
   doc: that's LEAPP's own internal framework plumbing, not a
   separately-published library).
3. **`Context` methods.** `crush_analyze/context.py` currently only
   implements `get_files_found()` and `get_relative_path()`. If the target
   module calls other `Context` methods (e.g. `context.get_seeker()`,
   `context.report_folder`), `Context` needs to be extended accordingly —
   again: reimplement, don't vendor the real iLEAPP `Context`/
   `FileSeekerDir`.
4. **Third-party deps.** New imports like `biplist`, `nska_deserialize`,
   etc. need to be added to `pyproject.toml` under `dependencies`. Check the
   license briefly (must be compatible with the project's Apache-2.0).
5. **Multiple artifact functions per file.** A script can declare more than
   one function in `__artifacts_v2__` (`applicationStateDB.py` declares
   three: `get_installed_apps`, `get_snapshot_creationDate`,
   `get_snapshot_lastUsedDate`). Each automatically becomes its own
   crush-analyze module id — nothing further to do, `leapp_compat/
   loader.py::artifacts_from_module` handles it.

## 2. Before vendoring: test in dev mode against the unmodified original

Don't copy right away — first run against the real, unmodified original
file:

```sh
crush-analyze run --module-path /path/to/original_file.py \
    --module <function-name> --dev \
    --input <test-directory> --output out.json
```

`--module` is only needed when the file declares more than one artifact
function (otherwise you get an error listing the available names). This
exercises step 1 in practice, before anything is vendored: missing
`ilapfuncs` symbols or `Context` methods show up here as a
`ModuleLoadError`.

## 3. Vendoring

Since the Android port, every vendored file lives under a
**platform subdirectory** — `crush_analyze/vendored/leapp/ios/` or
`crush_analyze/vendored/leapp/android/` (a future platform would get its own
directory the same way) — each with its own `MANIFEST.toml`.
`ModuleInfo.platform` is set automatically from the directory name when
loading (`modules/__init__.py::_load_vendored_modules()`) — nothing to
enter manually.

1. Copy the file **byte-identical** to
   `crush_analyze/vendored/leapp/<platform>/<name>.py`, where `<platform>`
   is `ios` or `android`. Never hand-edit it — any desired change means
   fetching a new commit upstream, not patching locally.
2. Note the commit hash of the source in the upstream repo (`git log -1
   --format=%H -- scripts/artifacts/<name>.py` in an iLEAPP/aLEAPP
   checkout, or via the GitHub API/history view:
   `api.github.com/repos/abrignoni/<repo>/commits?path=scripts/artifacts/<name>.py&per_page=1`).
3. Compute the sha256 of the vendored file:
   ```sh
   sha256sum crush_analyze/vendored/leapp/<platform>/<name>.py
   ```
4. Add an entry to `crush_analyze/vendored/leapp/<platform>/MANIFEST.toml`,
   matching the existing `applicationStateDB.py`/`installedappsVending.py`
   entries:
   ```toml
   [[files]]
   name = "<name>.py"
   upstream_repo = "https://github.com/abrignoni/<iLEAPP|aLEAPP>"
   upstream_path = "scripts/artifacts/<name>.py"
   upstream_commit = "<full commit hash>"
   upstream_license = "MIT"
   fetched_at = "YYYY-MM-DD"
   sha256 = "<sha256 from above>"
   ```
5. `LICENSE` next to `vendored/leapp/` already covers both iLEAPP **and**
   aLEAPP files (same author, same MIT license in both repos) — one shared
   license file, no per-module or per-platform duplicate needed.
6. **Non-artifact helper files** (a script imports a function from another
   file under `scripts/artifacts/…`, not from `scripts.ilapfuncs` — see the
   Android example `storagePathViews.py` below) belong in a `_helpers/`
   subdirectory of the relevant platform folder, e.g.
   `vendored/leapp/android/_helpers/<name>.py`, with its own
   `MANIFEST.toml` entry (`name = "_helpers/<name>.py"`). The leading
   underscore matters: `_load_vendored_modules()` only scans the direct
   `*.py` children of a platform folder for `__artifacts_v2__` — a helper
   file sitting right next to them would otherwise produce a misleading
   "could not load" warning on every run even though nothing is broken.

## 4. Verify registration

Nothing further to wire up: `modules/__init__.py::_load_vendored_modules()`
walks every `*.py` file directly under each `vendored/leapp/<platform>/` on
import and registers every artifact function it finds automatically, with
`platform` set from the directory name. Quick check:

```sh
crush-analyze list-modules
```

— the output carries a `"platform"` field per module. If loading a single
file fails (e.g. a missing optional dependency), only a warning is printed
to stderr and the rest of the modules stay usable — that's intended
behavior, not something to work around. If this warning shows up for a file
that isn't actually an artifact module (see point 6 above), the file
belongs in `_helpers/`.

## 5. Tests

For the compat shim itself, see `tests/test_leapp_compat.py` as a template
(synthetic mini-modules, no real fixtures). For an actual vendored module,
see `tests/test_runner.py::test_run_real_vendored_installed_apps_module_
against_a_synthetic_fixture` (iOS, SQLite + binary plist) and
`test_run_real_vendored_installedapps_vending_module_against_a_synthetic_
fixture` (Android, plain SQLite) as templates — both build the fixture
source file at test run time inside the test itself (no binary fixture
checked into the repo), run end to end through `runner.run()`, and assert
`status`, `analyzer.platform`, and the produced `rows[]` against an
expected value. For a new module, reuse the same build-the-fixture-in-the-
test approach, plus:

- Build a small fixture file (SQLite DB and/or plist) with synthetic but
  structurally real data — only the fields the parser actually reads.
- Run it end to end through `runner.run()` (or the CLI) and check columns +
  rows against an expected snapshot.
- Explicitly test the no-source-file / empty-DB case, so a "harmlessly
  empty" result never accidentally passes as success.

Then:

```sh
pytest
ruff check .
mypy .
```

`vendored/` is excluded from `ruff` (`extend-exclude`) and `mypy`
(`exclude`) in `pyproject.toml` — the vendored file itself doesn't need to
pass the project's lint rules, only the shim/tests around it do.

## 6. Known pitfalls (learned from the real ports so far)

- **JSON serialization:** plist values routinely come back as real
  `datetime` or `bytes` objects. `crush_analyze.json_safe` already handles
  this (datetimes → ISO-8601 string, bytes → hex) — nothing to do in the
  module itself.
- **Column types:** `_column_from_header` in `leapp_compat/loader.py` only
  accepts `string | int | float | bool | datetime` as a column type;
  anything else (including a typo in the original header tuple) silently
  falls back to `"string"`. For modules with many typed columns it's worth
  manually comparing the produced `columns[]` against expectations.
- **The `source_path` return value** from the LEAPP tuple is discarded —
  contract v1 already carries the path via `run.input_path`.
- **Cross-file imports on other `scripts/artifacts/*` files** (not just
  `scripts.ilapfuncs`): `installedappsVending.py` additionally imports
  `from scripts.artifacts.storagePathViews import unique_files` — a
  standalone, non-`__artifacts_v2__` helper module shared by other Android
  artifact scripts. So the compatibility check in step 1 shouldn't only
  look for `from scripts.ilapfuncs import ...` at the top of the file, but
  for any `from scripts...import` in general. Such a helper module gets
  vendored exactly like an artifact script (step 3, point 6 above), but
  placed under `_helpers/` and registered in `sys.modules` under its full
  `scripts.artifacts.<name>` path by
  `leapp_compat.loader.install_scripts_shim()` — parallel to, but a
  separate code path from, the `scripts.ilapfuncs` registration.
- **`platform` on `ModuleInfo`** comes automatically from the platform
  subdirectory (step 3) and flows unchanged into `analyzer.platform` in the
  contract v1 JSON as well as into the `list-modules` output — nothing to
  do in the module itself, the file just needs to live in the right
  `ios/`/`android/` folder.
