import os
from pathlib import Path
from tempfile import NamedTemporaryFile
from unittest.mock import patch, call

import pytest

from pilot.helpers.files import get_file_contents, get_directory_contents, update_file


@patch("pilot.helpers.files.open")
@patch("pilot.helpers.files.os")
def test_update_file_creates_directories(mock_os, mock_open):
    """Test that update_file creates intermediate directories if they don't exist."""

    mock_os.path.dirname = os.path.dirname
    update_file("/path/to/file", "content")
    mock_os.makedirs.assert_called_once_with("/path/to", exist_ok=True)


@patch("pilot.helpers.files.open")
@patch("pilot.helpers.files.os")
def test_update_file_creates_text_file(mock_os, mock_open):
    """Test that update_file creates intermediate directories if they don't exist."""

    update_file("/path/to/file", "無為")
    mock_open.assert_called_once_with("/path/to/file", "w", encoding="utf-8")
    mock_open.return_value.__enter__.return_value.write.assert_called_once_with("無為")


@patch("pilot.helpers.files.open")
@patch("pilot.helpers.files.os")
def test_update_file_creates_binary_file(mock_os, mock_open):
    """Test that update_file creates intermediate directories if they don't exist."""

    update_file("/path/to/file", b"\x00\x00\x00")
    mock_open.assert_called_once_with("/path/to/file", "wb", encoding=None)
    mock_open.return_value.__enter__.return_value.write.assert_called_once_with(b"\x00\x00\x00")


@pytest.mark.parametrize(
    ("source", "expected_encoded"),
    [
        ("file.txt", b"file.txt"),
        ("foo.txt - 無為", b"foo.txt - \xe7\x84\xa1\xe7\x82\xba"),
        (b"\xff\xff\xff", b"\xff\xff\xff"),
    ],
)
def test_update_file_with_encoded_content(source, expected_encoded):
    # Can't use NamedTemporaryFile this as a context manager because Windows
    # doesn't allow O_TEMPORARY files (with delete=True) to be opened
    # twice, defeating the purpose.
    file = NamedTemporaryFile(delete=False)
    update_file(file.name, source)
    assert file.read() == expected_encoded

    file.close()
    os.remove(file.name)

@pytest.mark.parametrize(
    ("encoded", "expected"),
    [
        (b"file.txt", "file.txt"),
        (b"foo.txt - \xe7\x84\xa1\xe7\x82\xba", "foo.txt - 無為"),
        (b"\xff\xff\xff", b"\xff\xff\xff"),
    ],
)
def test_get_file_contents(encoded, expected):
    file = NamedTemporaryFile(delete=False)
    file.write(encoded)
    file.flush()

    file_path = Path(file.name)
    data = get_file_contents(file.name, file_path.anchor)
    assert data == {
        "content": expected,
        "name": file_path.name,
        "path": str(file_path.parent.relative_to(file_path.anchor)),
        "full_path": file.name,
        "lines_of_code": 1,
    }
    file.close()
    os.remove(file.name)

@patch("pilot.helpers.files.open")
@patch("pilot.helpers.files.os")
@patch("pilot.helpers.files.IgnoreMatcher")
def test_get_directory_contents_mocked(mock_IgnoreMatcher, mock_os, mock_open):
    """
    Test that get_directory_contents traverses the directory tree,
    ignores specified ignore files/folders, and can handle both
    text and binary files.
    """

    # Normalize path to use correct path separators
    def np(path: str) -> str:
        return str(Path(path))

    mock_os.path.join = os.path.join
    mock_os.path.normpath = os.path.normpath
    mock_os.path.basename = os.path.basename
    mock_IgnoreMatcher.return_value.ignore = lambda path: os.path.basename(path) in ["to-ignore", "to-ignore.txt"]

    mock_walk = mock_os.walk
    mock_walk.return_value = [
        (np("/fake/root"), ["foo", "to-ignore", "bar"], ["file.txt", "to-ignore.txt"]),
        (np("/fake/root/foo"), [], ["foo.txt"]),
        (np("/fake/root/bar"), [], ["bar.txt"]),
    ]
    mock_open.return_value.__enter__.return_value.read.side_effect = [
        "file.txt",
        "foo.txt - 無為",
        UnicodeDecodeError("utf-8", b"\xff\xff\xff", 0, 1, "invalid start byte"),
        b"\xff\xff\xff",
    ]

    data = get_directory_contents(np("/fake/root"), ["to-ignore", "to-ignore.txt"])
    assert data == [
        {
            "content": "file.txt",
            "full_path": np("/fake/root/file.txt"),
            'lines_of_code': 1,
            "name": "file.txt",
            "path": "",
        },
        {
            "content": "foo.txt - 無為",
            "full_path": np("/fake/root/foo/foo.txt"),
            'lines_of_code': 1,
            "name": "foo.txt",
            "path": "foo",
        },
        {
            "content": b"\xff\xff\xff",
            "full_path": np("/fake/root/bar/bar.txt"),
            'lines_of_code': 1,
            "name": "bar.txt",
            "path": "bar",
        },
    ]
    mock_walk.assert_called_once_with(np("/fake/root"))


def test_get_directory_contents_live():
    files = get_directory_contents(
        os.path.dirname(os.path.dirname(__file__)), [".pytest_cache", "agents", "__init__.py"]
    )

    # Check this file was loaded as a text file
    this_file = [f for f in files if f["name"] == "test_files.py"][0]
    assert this_file["path"] == "helpers"
    assert this_file["full_path"] == __file__
    assert isinstance(this_file["content"], str)
    assert "test_get_directory_contents_live()" in this_file["content"]

    # Check that the binary file was ignored
    image_files = [
        f
        for f in files
        if f["path"] == "helpers" and f["name"] == "testlogo.png"
    ]
    assert image_files == []

    # Check that the ignore list works
    assert all(file["name"] != "__init__.py" for file in files)
    assert any(file["path"] == "database" for file in files)
