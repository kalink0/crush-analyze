"""Bundles crush_analyze's non-.py data files (vendored/leapp/*.toml,
vendored/leapp/LICENSE) into a PyInstaller build. Setuptools' own package
discovery already picks up vendored/leapp/*.py as ordinary module files;
this hook covers only what that discovery misses."""

from PyInstaller.utils.hooks import collect_data_files

datas = collect_data_files("crush_analyze")
