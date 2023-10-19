import builtins

# Save the original 'open' function to avoid infinite recursion
built_in_open = builtins.open


def open(file, *args, **kwargs):
    # If encoding is not specified and it's not binary mode, set it to 'utf-8'
    if 'encoding' not in kwargs and 'b' not in args:
        kwargs['encoding'] = 'utf-8'

    # Call the original 'open' function with potentially modified arguments
    return built_in_open(file, *args, **kwargs)


# Override the built-in 'open' with our version
builtins.open = open
