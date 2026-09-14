from __future__ import annotations

from pathlib import Path

from crush_analyze.context import Context, find_files


def test_find_files_matches_glob_pattern_recursively(tmp_path: Path) -> None:
    (tmp_path / "a.plist").write_text("x")
    nested = tmp_path / "nested"
    nested.mkdir()
    (nested / "b.plist").write_text("x")
    (nested / "c.txt").write_text("x")

    found = find_files(tmp_path, ["*.plist"])

    assert found == sorted([tmp_path / "a.plist", nested / "b.plist"])


def test_find_files_ignores_directories(tmp_path: Path) -> None:
    (tmp_path / "sub.plist").mkdir()

    found = find_files(tmp_path, ["*.plist"])

    assert found == []


def test_get_relative_path_is_relative_to_input_path(tmp_path: Path) -> None:
    context = Context(input_path=tmp_path, files_found=[])

    assert context.get_relative_path(str(tmp_path / "a" / "b.txt")) == str(Path("a") / "b.txt")


def test_get_files_found_returns_strings(tmp_path: Path) -> None:
    files = [tmp_path / "a.txt", tmp_path / "b.txt"]
    context = Context(input_path=tmp_path, files_found=files)

    assert context.get_files_found() == [str(f) for f in files]
