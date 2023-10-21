import builtins
from typing import IO
# Save the original 'open' function to avoid infinite recursion
built_in_open = builtins.open


def get_custom_open(file, *args, **kwargs) -> IO:
    """
    Custom `open` function with default 'utf-8' encoding unless binary mode or encoding is specified.

    Parameters:
    - file (str): File to open.
    - *args: Arguments for built-in open function.
    - **kwargs: Keyword arguments for built-in open function.

    Returns:
    IO: File object.
    """

    # Check for binary mode
    binary_mode = any('b' in arg for arg in args)

    # Set default encoding to 'utf-8' if not specified and not in binary mode
    if 'encoding' not in kwargs and not binary_mode:
        kwargs['encoding'] = 'utf-8'

    # Call the original 'open' function
    return built_in_open(file, *args, **kwargs)
