import os
import os.path
from hashlib import sha1
from pathlib import Path

from core.disk.ignore import IgnoreMatcher
from core.log import get_logger

log = get_logger(__name__)


class VirtualFileSystem:
    def save(self, path: str, content: str):
        """
        Save content to a file. Use for both new and updated files.

        :param path: Path to the file, relative to project root.
        :param content: Content to save.
        """
        raise NotImplementedError()

    def read(self, path: str) -> str:
        """
        Read file contents.

        :param path: Path to the file, relative to project root.
        :return: File contents.
        """
        raise NotImplementedError()

    def remove(self, path: str):
        """
        Remove a file.

        If file doesn't exist or is a directory, or if the file is ignored,
        do nothing.

        :param path: Path to the file, relative to project root.
        """
        raise NotImplementedError()

    def get_full_path(self, path: str) -> str:
        """
        Get the full path to a file.

        This should be used to check the full path of the file on whichever
        file system it locally is stored. For example, getting a full path
        to a file and then passing it to an external program via run_command
        should work.

        :param path: Path to the file, relative to project root.
        :return: Full path to the file.
        """
        raise NotImplementedError()

    def _filter_by_prefix(self, file_list: list[str], prefix: str) -> list[str]:
        # We use "/" internally on all platforms, including win32
        if not prefix.endswith("/"):
            prefix = prefix + "/"
        return [f for f in file_list if f.startswith(prefix)]

    def _get_file_list(self) -> list[str]:
        raise NotImplementedError()

    def list(self, prefix: str = None) -> list[str]:
        """
        Return a list of files in the project.

        File paths are relative to the project root.

        :param prefix: Optional prefix to filter files for.
        :return: List of file paths.
        """
        retval = sorted(self._get_file_list())
        if prefix:
            retval = self._filter_by_prefix(retval, prefix)
        return retval

    def hash(self, path: str) -> str:
        content = self.read(path)
        return self.hash_string(content)

    @staticmethod
    def hash_string(content: str) -> str:
        return sha1(content.encode("utf-8")).hexdigest()


class MemoryVFS(VirtualFileSystem):
    files: dict[str, str]

    def __init__(self):
        self.files = {}

    def save(self, path: str, content: str):
        self.files[path] = content

    def read(self, path: str) -> str:
        try:
            return self.files[path]
        except KeyError:
            raise ValueError(f"File not found: {path}")

    def remove(self, path: str):
        if path in self.files:
            del self.files[path]

    def get_full_path(self, path: str) -> str:
        # We use "/" internally on all platforms, including win32
        return "/" + path

    def _get_file_list(self) -> list[str]:
        return self.files.keys()


class LocalDiskVFS(VirtualFileSystem):
    def __init__(
        self,
        root: str,
        create: bool = True,
        allow_existing: bool = True,
        ignore_matcher: IgnoreMatcher = None,
    ):
        if not os.path.isdir(root):
            if create:
                os.makedirs(root)
            else:
                raise ValueError(f"Root directory does not exist: {root}")
        else:
            if not allow_existing:
                raise FileExistsError(f"Root directory already exists: {root}")

        if ignore_matcher is None:
            ignore_matcher = IgnoreMatcher(root, [])

        self.root = root
        self.ignore_matcher = ignore_matcher

    def get_full_path(self, path: str) -> str:
        return os.path.abspath(os.path.normpath(os.path.join(self.root, path)))

    def save(self, path: str, content: str):
        full_path = self.get_full_path(path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(content)
        log.debug(f"Saved file {path} ({len(content)} bytes) to {full_path}")

    def read(self, path: str) -> str:
        full_path = self.get_full_path(path)
        if not os.path.isfile(full_path):
            raise ValueError(f"File not found: {path}")

        # TODO: do we want error handling here?
        with open(full_path, "r", encoding="utf-8") as f:
            return f.read()

    def remove(self, path: str):
        if self.ignore_matcher.ignore(path):
            return

        full_path = self.get_full_path(path)
        if os.path.isfile(full_path):
            try:
                os.remove(full_path)
                log.debug(f"Removed file {path} from {full_path}")
            except Exception as err:  # noqa
                log.error(f"Failed to remove file {path}: {err}", exc_info=True)

    def _get_file_list(self) -> list[str]:
        files = []
        for dpath, dirnames, filenames in os.walk(self.root):
            # Modify in place to prevent recursing into ignored directories
            dirnames[:] = [
                d
                for d in dirnames
                if not self.ignore_matcher.ignore(os.path.relpath(os.path.join(dpath, d), self.root))
            ]

            for filename in filenames:
                path = os.path.relpath(os.path.join(dpath, filename), self.root)
                if not self.ignore_matcher.ignore(path):
                    # We use "/" internally on all platforms, including win32
                    files.append(Path(path).as_posix())

        return files


__all__ = ["VirtualFileSystem", "MemoryVFS", "LocalDiskVFS"]
