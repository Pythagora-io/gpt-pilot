from io import StringIO
from os.path import join
from unittest.mock import MagicMock, patch

import pytest

from core.disk.ignore import IgnoreMatcher


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("test.py", False),
        ("test.pyc", True),
        (join("module", "test.py"), False),
        (join("module", "test.pyc"), True),
        ("node_modules", True),
        (join("docs", "_build"), True),
        (join("some", "lower", "dir"), True),
        (join("tests", "some", "lower", "dir"), False),
        (join("module", "migrations", "0001_initial.py"), True),
        (join("module", "another", "migrations", "0001_initial.py"), True),
        (join("module", "migrations", "0001_initial.json"), False),
    ],
)
@patch("os.path.isfile", return_value=True)
@patch("builtins.open", return_value=MagicMock(read=StringIO("")))
def test_ignore_paths(_mock_open, _mock_isfile, path, expected):
    matcher = IgnoreMatcher(
        "/tmp",
        [
            "*.pyc",
            "node_modules",
            "_build",
            "some/lower/dir",
            "*/migrations/*.py",
        ],
    )
    assert matcher.ignore(path) == expected


@pytest.mark.parametrize(
    ("path", "size", "expected"),
    [
        ("test.py", 100, False),
        ("test.py", 101, True),
    ],
)
@patch("os.path.isfile", return_value=True)
@patch("builtins.open", return_value=MagicMock(read=StringIO("")))
@patch("os.path.getsize")
def test_ignore_large_files(
    _mock_getsize,
    _mock_open,
    _mock_isfile,
    path,
    size,
    expected,
):
    _mock_getsize.return_value = size
    matcher = IgnoreMatcher("/tmp", [], ignore_size_threshold=100)
    assert matcher.ignore(path) == expected


@patch("os.path.isfile", return_value=True)
@patch("builtins.open")
def test_ignore_binary(_mock_open, _mock_isfile):
    _mock_open.return_value.__enter__.return_value.read.side_effect = UnicodeDecodeError(
        "utf-8", b"", 0, 1, "invalid start byte"
    )
    matcher = IgnoreMatcher("/tmp", [])
    assert matcher.ignore("test.py") is True
