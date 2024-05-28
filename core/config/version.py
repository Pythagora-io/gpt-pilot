import re
from os.path import abspath, basename, dirname, isdir, isfile, join
from typing import Optional

GIT_DIR_PATH = abspath(join(dirname(__file__), "..", "..", ".git"))


def get_git_commit() -> Optional[str]:
    """
    Return the current git commit (if running from a repo).

    :return: commit hash or None if not running from a git repo
    """

    if not isdir(GIT_DIR_PATH):
        return None

    git_head = join(GIT_DIR_PATH, "HEAD")
    if not isfile(git_head):
        return None

    with open(git_head, "r", encoding="utf-8") as f:
        ref = f.read().strip()

    # Direct reference to commit hash
    if not ref.startswith("ref: "):
        return ref

    # Follow the reference
    ref = ref[5:]
    ref_path = join(GIT_DIR_PATH, ref)

    # Dangling reference,  return the reference name
    if not isfile(ref_path):
        return basename(ref_path)

    # Return the reference commit hash
    with open(ref_path, "r", encoding="utf-8") as f:
        return f.read().strip()


def get_package_version() -> str:
    """
    Get package version as defined pyproject.toml.

    If not found, returns "0.0.0."

    :return: package version as defined in pyproject.toml
    """
    UNKNOWN = "0.0.0"
    PYPOETRY_VERSION_PATTERN = re.compile(r'^\s*version\s*=\s*"(.*)"\s*(#.*)?$')

    pyproject_path = join(dirname(__file__), "..", "..", "pyproject.toml")
    if not isfile(pyproject_path):
        return UNKNOWN

    with open(pyproject_path, "r", encoding="utf-8") as fp:
        for line in fp:
            m = PYPOETRY_VERSION_PATTERN.match(line)
            if m:
                return m.group(1)

    return UNKNOWN


def get_version() -> str:
    """
    Find and return the current version of Pythagora Core.

    The version string is built from the package version and the current
    git commit hash (if running from a git repo).

    Example: 0.0.0-gitbf01c19

    :return: version string
    """

    version = get_package_version()
    commit = get_git_commit()
    if commit:
        version = version + "-git" + commit[:7]

    return version


__all__ = ["get_version"]
