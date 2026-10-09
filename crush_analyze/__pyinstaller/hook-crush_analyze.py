"""Bundles what PyInstaller's import analysis can't see on its own:

- vendored/**/*.py as real files on disk, not just compiled into the PYZ
  archive -- modules/__init__.py discovers vendored LEAPP modules by
  globbing for *.py files and leapp_compat/loader.py execs them by path;
- the non-.py files next to them (MANIFEST.toml, LICENSE);
- the third-party modules those vendored files import, as hiddenimports
  (see `vendored_imports`)."""

from PyInstaller.utils.hooks import collect_data_files

from crush_analyze.__pyinstaller import vendored_imports

datas = collect_data_files(
    "crush_analyze", include_py_files=True, subdir="vendored", excludes=["**/__pycache__"]
)
hiddenimports = vendored_imports()
