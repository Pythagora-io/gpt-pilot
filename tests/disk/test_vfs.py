from os.path import exists, join
from pathlib import Path

import pytest

from core.disk.ignore import IgnoreMatcher
from core.disk.vfs import LocalDiskVFS, MemoryVFS


def test_memory_vfs():
    vfs = MemoryVFS()

    assert vfs.list() == []

    vfs.save("test.txt", "hello world")
    assert vfs.read("test.txt") == "hello world"
    assert vfs.list() == ["test.txt"]

    vfs.save("subdir/another.txt", "hello world")
    assert vfs.read("subdir/another.txt") == "hello world"
    assert vfs.list() == ["subdir/another.txt", "test.txt"]

    assert vfs.list("subdir") == ["subdir/another.txt"]
    assert vfs.list("subdir/") == ["subdir/another.txt"]

    assert vfs.list("nonexistent") == []

    vfs.remove("test.txt")
    assert vfs.list() == ["subdir/another.txt"]

    vfs.remove("nonexistent.txt")


def test_local_disk_vfs(tmp_path):
    vfs = LocalDiskVFS(tmp_path)

    assert vfs.list() == []

    vfs.save("test.txt", "hello world")
    assert vfs.read("test.txt") == "hello world"
    assert vfs.list() == ["test.txt"]

    vfs.save("subdir/another.txt", "hello world")
    assert vfs.read("subdir/another.txt") == "hello world"
    assert vfs.list() == ["subdir/another.txt", "test.txt"]

    assert vfs.list("subdir") == ["subdir/another.txt"]
    assert vfs.list("subdir/") == ["subdir/another.txt"]

    assert vfs.list("nonexistent") == []

    vfs.remove("test.txt")
    assert vfs.list() == ["subdir/another.txt"]

    vfs.remove("nonexistent.txt")


def test_local_disk_vfs_with_matcher(tmp_path):
    matcher = IgnoreMatcher(tmp_path, ["*.log"])
    vfs = LocalDiskVFS(tmp_path, ignore_matcher=matcher)

    with open(join(tmp_path, "test.log"), "w") as f:
        f.write("this should be ignored")

    assert vfs.list() == []

    with open(join(tmp_path, "test.txt"), "w") as f:
        f.write("hello world")

    assert vfs.list() == ["test.txt"]
    assert vfs.read("test.txt") == "hello world"

    vfs.save("subdir/another.txt", "hello world")
    assert exists(join(tmp_path, "subdir", "another.txt"))

    assert vfs.read("subdir/another.txt") == "hello world"
    assert vfs.list() == ["subdir/another.txt", "test.txt"]

    assert vfs.list("subdir") == ["subdir/another.txt"]
    assert vfs.list("subdir/") == ["subdir/another.txt"]

    assert vfs.list("nonexistent") == []

    vfs.remove("test.txt")
    assert vfs.list() == ["subdir/another.txt"]
    assert not exists(join(tmp_path, "test.txt"))

    vfs.remove("nonexistent.txt")

    vfs.remove("test.log")
    assert exists(join(tmp_path, "test.log"))


@pytest.mark.parametrize("operation", ["save", "read", "remove", "get_full_path"])
@pytest.mark.parametrize("path_kind", ["relative", "absolute", "sibling"])
def test_local_disk_vfs_rejects_paths_outside_root(tmp_path, operation, path_kind):
    root = tmp_path / "workspace"
    vfs = LocalDiskVFS(root)
    outside = tmp_path / ("workspace-other" if path_kind == "sibling" else "outside") / "file.txt"
    outside.parent.mkdir()
    outside.write_text("keep", encoding="utf-8")
    path = "../outside/file.txt" if path_kind == "relative" else str(outside)

    with pytest.raises(ValueError, match="outside the project root"):
        if operation == "save":
            vfs.save(path, "replacement")
        else:
            getattr(vfs, operation)(path)

    assert outside.read_text(encoding="utf-8") == "keep"


def test_local_disk_vfs_resolves_paths_inside_root(tmp_path):
    vfs = LocalDiskVFS(tmp_path)
    vfs.save("subdir/../file.txt", "hello")

    assert vfs.get_full_path("subdir/../file.txt") == str(tmp_path / "file.txt")
    assert vfs.get_full_path(".") == str(tmp_path.resolve())
    assert vfs.get_full_path(str(tmp_path / "file.txt")) == str(tmp_path / "file.txt")
    assert vfs.read("./file.txt") == "hello"


def test_local_disk_vfs_rejects_symlinks_outside_root(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    root = tmp_path / "workspace"
    vfs = LocalDiskVFS(root)
    link = root / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"Creating symlinks is unavailable: {error}")

    with pytest.raises(ValueError, match="outside the project root"):
        vfs.save("link/file.txt", "replacement")

    assert not (outside / "file.txt").exists()


def test_local_disk_vfs_remove_preserves_resolved_target(tmp_path, monkeypatch):
    # Emulate symlink resolution so the removal boundary is covered without symlink privileges.
    vfs = LocalDiskVFS(tmp_path)
    target = tmp_path / "target.txt"
    target.write_text("keep", encoding="utf-8")
    alias = tmp_path / "alias.txt"
    alias.write_text("alias", encoding="utf-8")
    original_resolve = Path.resolve

    def resolve(path, *args, **kwargs):
        return target if path == alias else original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)

    vfs.remove("alias.txt")

    assert not alias.exists()
    assert target.read_text(encoding="utf-8") == "keep"


@pytest.mark.parametrize("operation", ["save", "read", "remove", "get_full_path"])
def test_local_disk_vfs_rejects_outside_path_resolving_inside_root(tmp_path, monkeypatch, operation):
    # An outside symlink must not become an allowed operation just because its target is inside.
    root = tmp_path / "workspace"
    vfs = LocalDiskVFS(root)
    target = root / "target.txt"
    target.write_text("keep", encoding="utf-8")
    alias = tmp_path / "alias.txt"
    alias.write_text("alias", encoding="utf-8")
    original_resolve = Path.resolve

    def resolve(path, *args, **kwargs):
        return target if path == alias else original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)

    with pytest.raises(ValueError, match="outside the project root"):
        if operation == "save":
            vfs.save(str(alias), "replacement")
        else:
            getattr(vfs, operation)(str(alias))

    assert alias.read_text(encoding="utf-8") == "alias"
    assert target.read_text(encoding="utf-8") == "keep"


def test_local_disk_vfs_removes_symlink_without_removing_target(tmp_path):
    vfs = LocalDiskVFS(tmp_path)
    target = tmp_path / "target.txt"
    target.write_text("keep", encoding="utf-8")
    alias = tmp_path / "alias.txt"
    try:
        alias.symlink_to(target)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"Creating symlinks is unavailable: {error}")

    assert vfs.get_full_path("alias.txt") == str(alias)
    vfs.remove("alias.txt")

    assert not alias.is_symlink()
    assert target.read_text(encoding="utf-8") == "keep"


def test_local_disk_vfs_rejects_outside_symlink_to_inside_root(tmp_path):
    root = tmp_path / "workspace"
    vfs = LocalDiskVFS(root)
    target = root / "target.txt"
    target.write_text("keep", encoding="utf-8")
    alias = tmp_path / "alias.txt"
    try:
        alias.symlink_to(target)
    except (NotImplementedError, OSError) as error:
        pytest.skip(f"Creating symlinks is unavailable: {error}")

    with pytest.raises(ValueError, match="outside the project root"):
        vfs.remove(str(alias))

    assert alias.is_symlink()
    assert target.read_text(encoding="utf-8") == "keep"
