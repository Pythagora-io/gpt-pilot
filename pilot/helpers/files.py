from pathlib import Path
import os
from typing import Optional, Union

from utils.style import color_green


def update_file(path: str, new_content: Union[str, bytes]):
    """
    Update file with the new content.

    :param path: Full path to the file
    :param new_content: New content to write to the file

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
        print({"path": path, "line": None}, type="openFile")
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
    try:
        # Assume it's a text file using UTF-8 encoding
        file_content = open(path, "r", encoding="utf-8").read()
    except UnicodeDecodeError:
        # If that fails, we'll treat it as a binary file
        file_content = open(path, "rb").read()
    except NotADirectoryError:
        raise ValueError(f"Path is not a directory: {path}")
    except FileNotFoundError:
        raise ValueError(f"File not found: {path}")

    file_name = os.path.basename(path)
    relative_path = str(Path(path).parent.relative_to(project_root_path))

    if relative_path == ".":
        relative_path = ""

    return {
        "name": file_name,
        "path": relative_path,
        "content": file_content,
        "full_path": path,
    }


def get_directory_contents(
    directory: str, ignore: Optional[list[str]] = None
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

    if ignore is None:
        ignore = []

    # TODO: Convert to use pathlib.Path.walk()
    for dpath, dirs, files in os.walk(directory):
        # In-place update of dirs so that os.walk() doesn't traverse them
        dirs[:] = [d for d in dirs if d not in ignore]

        for file in files:
            if file in ignore:
                continue

            return_array.append(get_file_contents(os.path.join(dpath, file), directory))

    return return_array


def clear_directory(directory: str, ignore: Optional[list[str]] = None):
    """
    Delete all files and directories (except ignored ones) in the given directory.

    :param dir_path: Full path to the directory to clear
    :param ignore: List of files or folders to ignore (optional)
    """
    if ignore is None:
        ignore = []

    # TODO: Convert to use pathlib.Path.walk()
    for dpath, dirs, files in os.walk(directory, topdown=True):
        # In-place update of dirs so that os.walk() doesn't traverse them
        dirs[:] = [d for d in dirs if d not in ignore]

        for file in files:
            if file in ignore or os.path.join(directory, file) in ignore:
                continue

            path = os.path.join(dpath, file)
            os.remove(path)

        # Delete empty subdirectories not in ignore list
        for d in dirs:
            subdir_path = os.path.join(dpath, d)
            if not os.listdir(subdir_path):
                os.rmdir(subdir_path)
