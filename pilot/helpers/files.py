from pathlib import Path
import os
from typing import Optional, Union

from utils.style import color_green
from utils.ignore import IgnoreMatcher

def update_file(path: str, new_content: Union[str, bytes], project=None):
    """
    Update file with the new content.

    :param path: Full path to the file
    :param new_content: New content to write to the file
    :param project: Optional; a Project object related to the file update. Default is None.

    Any intermediate directories will be created if they don't exist.
    If file is text, it will be written using UTF-8 encoding.
    """
    # TODO: we should know where project root is and ensure no
    # files are written outside of it.
    os.makedirs(os.path.dirname(path), exist_ok=True)

    if isinstance(new_content, str):
        file_mode = "w"
        encoding = "utf-8"
    else:
        file_mode = "wb"
        encoding = None

    with open(path, file_mode, encoding=encoding) as file:
        file.write(new_content)
        if project is not None:  # project can be None only in tests
            if not project.skip_steps:
                print({"path": path, "line": None}, type='openFile')
            if not project.check_ipc():
                print(color_green(f"Updated file {path}"))


def get_file_contents(
    path: str, project_root_path: str
) -> dict[str, Union[str, bytes]]:
    """
    Get file content and metadata.

    :param path: Full path to the file
    :param project_root_path: Full path to the project root directory
    :return: Object with the following keys:
        - name: File name
        - path: Relative path to the file
        - content: File content (str or bytes)
        - full_path: Full path to the file

    If file is text, it will be read using UTF-8 encoding and `content`
    will be a Python string. If that fails, it will be treated as a
    binary file and `content` will be a Python bytes object.
    """
    # Normalize the path to avoid issues with different path separators
    full_path = os.path.normpath(path)

    try:
        # Assume it's a text file using UTF-8 encoding
        with open(full_path, "r", encoding="utf-8") as file:
            file_content = file.read()
    except UnicodeDecodeError:
        # If that fails, we'll treat it as a binary file
        with open(full_path, "rb") as file:
            file_content = file.read()
    except NotADirectoryError:
        raise ValueError(f"Path is not a directory: {path}")
    except FileNotFoundError:
        raise ValueError(f"File not found: {full_path}")
    except Exception as e:
        raise ValueError(f"Exception in get_file_contents: {e}")

    file_name = os.path.basename(path)
    relative_path = str(Path(path).parent.relative_to(project_root_path))

    if relative_path == '.':
        relative_path = ''

    return {
        "name": file_name,
        "path": relative_path,
        "content": file_content,
        "full_path": full_path,
        "lines_of_code": len(file_content.splitlines()),
    }


def get_directory_contents(
    directory: str,
    ignore: Optional[list[str]] = None,
) -> list[dict[str, Union[str, bytes]]]:
    """
    Get the content of all files in the given directory.

    :param directory: Full path to the directory to search
    :param ignore: List of files or folders to ignore (optional)
    :return: List of file objects as returned by `get_file_contents`

    See `get_file_contents()` for the details on the output structure
    and how files are read.
    """
    return_array = []

    matcher = IgnoreMatcher(ignore, root_path=directory)

    # TODO: Convert to use pathlib.Path.walk()
    for dpath, dirs, files in os.walk(directory):
        # In-place update of dirs so that os.walk() doesn't traverse them
        dirs[:] = [
            d for d in dirs
            if not matcher.ignore(os.path.join(dpath, d))
        ]

        for file in files:
            full_path = os.path.join(dpath, file)
            if matcher.ignore(full_path):
                continue

            return_array.append(get_file_contents(full_path, directory))

    return return_array


def clear_directory(directory: str, ignore: Optional[list[str]] = None):
    """
    Delete all files and directories (except ignored ones) in the given directory.

    :param dir_path: Full path to the directory to clear
    :param ignore: List of files or folders to ignore (optional)
    """
    matcher = IgnoreMatcher(ignore, root_path=directory)

    # TODO: Convert to use pathlib.Path.walk()
    for dpath, dirs, files in os.walk(directory, topdown=True):
        # In-place update of dirs so that os.walk() doesn't traverse them
        dirs[:] = [
            d for d in dirs
            if not matcher.ignore(os.path.join(dpath, d))
        ]

        for file in files:
            full_path = os.path.join(dpath, file)
            if matcher.ignore(full_path):
                continue

            os.remove(full_path)

        # Delete empty subdirectories not in ignore list
        for d in dirs:
            subdir_path = os.path.join(dpath, d)
            if not os.listdir(subdir_path):
                os.rmdir(subdir_path)
