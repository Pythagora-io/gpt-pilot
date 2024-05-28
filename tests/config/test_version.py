from os.path import dirname, join
from subprocess import check_output
from unittest.mock import patch

from core.config.version import get_git_commit, get_package_version, get_version


def test_get_package_version():
    with open(join(dirname(__file__), "..", "..", "pyproject.toml"), "r", encoding="utf-8") as f:
        pyproject_toml = f.read()

    version = get_package_version()
    assert version in pyproject_toml


def test_get_git_version():
    commit_from_git = check_output(["git", "rev-parse", "HEAD"]).decode("utf-8").strip()
    git_commit = get_git_commit()
    assert git_commit == commit_from_git


@patch("core.config.version.get_git_commit", return_value="abc")
@patch("core.config.version.get_package_version", return_value="1.2.3")
def test_get_version(_mock_get_package_version, _mock_get_git_commit):
    version = get_version()
    assert version == "1.2.3-gitabc"
