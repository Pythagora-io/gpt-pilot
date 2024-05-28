import os.path
from fnmatch import fnmatch
from typing import Optional


class IgnoreMatcher:
    """
    A class to match paths against a list of ignore patterns or
    file attributes (size, type).
    """

    def __init__(
        self,
        root_path: str,
        ignore_paths: list[str],
        *,
        ignore_size_threshold: Optional[int] = None,
    ):
        """
        Initialize the IgnoreMatcher object.

        Ignore paths are matched agains the file name and the full path,
        and may include shell-like wildcards ("*" for any number of characters,
        "?" for a single character). Paths are normalized, so "/" works on both
        Unix and Windows, and Windows matching is case insensitive.

        :param root_path: Root path to use when checking files on disk.
        :param ignore_paths: List of patterns to ignore.
        :param ignore_size_threshold: Files larger than this size will be ignored.
        """
        self.root_path = root_path
        self.ignore_paths = ignore_paths
        self.ignore_size_threshold = ignore_size_threshold

    def ignore(self, path: str) -> bool:
        """
        Check if the given path matches any of the ignore patterns.

        :param path: (Relative) path to the file or directory to check
        :return: True if the path matches any of the ignore patterns, False otherwise
        """

        full_path = os.path.normpath(os.path.join(self.root_path, path))

        if self._is_in_ignore_list(path):
            return True

        if self._is_large_file(full_path):
            return True

        # Binary files are always ignored
        if self._is_binary(full_path):
            return True

        return False

    def _is_in_ignore_list(self, path: str) -> bool:
        """
        Check if the given path matches any of the ignore patterns.

        Both the (relative) file path and the file (base) name are matched.

        :param path: The path to the file or directory to check
        :return: True if the path matches any of the ignore patterns, False otherwise.
        """
        name = os.path.basename(path)
        for pattern in self.ignore_paths:
            if fnmatch(name, pattern) or fnmatch(path, pattern):
                return True
        return False

    def _is_large_file(self, full_path: str) -> bool:
        """
        Check if the given file is larger than the threshold.

        This also returns True if the file doesn't or is not a regular file (eg.
        it's a symlink), since we want to ignore those kinds of files as well.

        :param path: Full path to the file to check.
        :return: True if the file is larger than the threshold, False otherwise.
        """
        if self.ignore_size_threshold is None:
            return False

        # We don't handle directories here
        if os.path.isdir(full_path):
            return False

        if not os.path.isfile(full_path):
            return True

        try:
            return bool(os.path.getsize(full_path) > self.ignore_size_threshold)
        except:  # noqa
            return True

    def _is_binary(self, full_path: str) -> bool:
        """
        Check if the given file is binary and should be ignored.

        This also returns True if the file doesn't or is not a regular file (eg.
        it's a symlink), or can't be opened, since we want to ignore those too.

        :param path: Full path to the file to check.
        :return: True if the file should be ignored, False otherwise.
        """

        # We don't handle directories here
        if os.path.isdir(full_path):
            return False

        if not os.path.isfile(full_path):
            return True

        try:
            with open(full_path, "r", encoding="utf-8") as f:
                f.read(128 * 1024)
            return False
        except:  # noqa
            # If we can't open the file for any reason (eg. PermissionError), it's
            # best to ignore it anyway
            return True


__all__ = ["IgnoreMatcher"]
