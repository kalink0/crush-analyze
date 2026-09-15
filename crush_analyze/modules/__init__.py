from __future__ import annotations

import sys
import tomllib
from pathlib import Path

from . import stub
from ..leapp_compat.loader import LeappModuleLoadError, load_leapp_module_file
from ..module_types import ModuleInfo, SourceInfo

_VENDORED_LEAPP_DIR = Path(__file__).resolve().parent.parent / "vendored" / "leapp"


class UnknownModuleError(Exception):
    pass


def _load_manifest(platform_dir: Path) -> dict[str, SourceInfo]:
    """Reads `platform_dir`'s MANIFEST.toml into a `{filename: SourceInfo}`
    lookup, `url` computed as a commit-pinned GitHub blob link. Missing or
    malformed manifest -> empty dict (each module in this platform dir then
    just gets `source=None`) rather than crashing module loading entirely --
    same "degrade, don't crash" standing rule as everything else here."""
    manifest_path = platform_dir / "MANIFEST.toml"
    if not manifest_path.is_file():
        return {}
    try:
        manifest = tomllib.loads(manifest_path.read_text())
    except tomllib.TOMLDecodeError as exc:
        print(f"warning: could not parse {manifest_path}: {exc}", file=sys.stderr)
        return {}

    sources: dict[str, SourceInfo] = {}
    for entry in manifest.get("files", []):
        repo = entry.get("upstream_repo")
        commit = entry.get("upstream_commit")
        path = entry.get("upstream_path")
        name = entry.get("name")
        if not (repo and commit and path and name):
            continue
        sources[name] = SourceInfo(repo=repo, commit=commit, path=path, url=f"{repo}/blob/{commit}/{path}")
    return sources


def _load_vendored_modules() -> list[ModuleInfo]:
    """Loads every vendored LEAPP artifact file under vendored/leapp/<platform>/
    -- one subdirectory per OS (currently "ios", "android"), which is also
    where each loaded module's `ModuleInfo.platform` comes from, and where
    that platform's MANIFEST.toml (see `_load_manifest`) gives each loaded
    module its `ModuleInfo.source`. A file that fails to load (e.g. a
    missing optional third-party dependency for one specific module, or a
    non-artifact helper file like android's storagePathViews.py, which has
    no __artifacts_v2__ of its own) is skipped with a warning rather than
    aborting the whole CLI — matches LEAPP's own "a module can disable
    itself" behavior, and means `list-modules` still reports everything
    that *is* usable."""
    infos: list[ModuleInfo] = []
    if not _VENDORED_LEAPP_DIR.is_dir():
        return infos
    for platform_dir in sorted(p for p in _VENDORED_LEAPP_DIR.iterdir() if p.is_dir()):
        sources = _load_manifest(platform_dir)
        for path in sorted(platform_dir.glob("*.py")):
            try:
                infos.extend(
                    load_leapp_module_file(
                        path, platform=platform_dir.name, source=sources.get(path.name)
                    )
                )
            except LeappModuleLoadError as exc:
                print(f"warning: could not load vendored module {path.name}: {exc}", file=sys.stderr)
    return infos


_MODULES: dict[str, ModuleInfo] = {stub.MODULE.id: stub.MODULE}
for _info in _load_vendored_modules():
    _MODULES[_info.id] = _info


def list_modules() -> list[dict[str, object]]:
    return [
        {
            "id": module.id,
            "name": module.name,
            "platform": module.platform,
            "source": module.source.to_dict() if module.source else None,
            "module_version": module.module_version,
            "requires": module.requires,
            "paths": module.paths,
        }
        for module in _MODULES.values()
    ]


def get_module(module_id: str) -> ModuleInfo:
    try:
        return _MODULES[module_id]
    except KeyError:
        raise UnknownModuleError(f"unknown module id: {module_id!r}") from None
