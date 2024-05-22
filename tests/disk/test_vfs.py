from os.path import exists, join

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
