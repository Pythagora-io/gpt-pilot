from __future__ import annotations

import os
from os import walk
from os.path import join, relpath
from pathlib import Path
from typing import Any, Callable

from jinja2 import Environment, FileSystemLoader


def escape_string(str: str) -> str:
    """
    Escape special characters in a string

    :param str: The string to escape
    :return: The escaped string
    """
    return str.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class Renderer:
    """
    Render a Jinja template

    Sets up Jinja renderer and renders one or more templates
    using provided context.

    * `render_template` renders a single template
    * `render_tree` renders all templates starting from a predefined
      root folder (which must reside inside templates folder structure)

    Rendered template(s) are returned as strings. Nothing is written
    to disk.

    Usage:

    >>> import Renderer from render
    >>> r = Renderer('path/to/templates')
    >>> output_string = r.render_template('template.html', {'key': 'value'})
    >>> output_tree = r.render_tree('tree/root', {'key': 'value'})
    """

    def __init__(self, template_dir: str):
        self.template_dir = template_dir
        self.jinja_env = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=False,
            lstrip_blocks=True,
            trim_blocks=True,
            keep_trailing_newline=True,
        )
        # Add filters here
        self.jinja_env.filters["escape_string"] = escape_string

    def render_template(self, template: str, context: Any) -> str:
        """
        Render a single template to a string using provided context

        :param template: Name of the template file, relative to `template_dir`.
        :param context: Context to render the template with.
        :return: The resulting string.
        """

        # Jinja2 always uses /, even on Windows
        template = template.replace("\\", "/")

        tpl_object = self.jinja_env.get_template(template)
        return tpl_object.render(context)

    def render_tree(self, root: str, context: Any, full_root_dir: str, filter: Callable = None) -> dict[str, str]:
        """
        Render a tree folder structure of templates using provided context

        :param root: Root of the tree (relative to `template_dir`).
        :param context: Context to render the templates with.
        :param full_root_dir: Full path to the root of the tree.
        :param filter: If defined, will be called for each file to check if it
        needs to be processed and determine output file path.
        :return: A flat dictionary with path => content structure.

        Root must be inside the template_dir (and must be specified relative
        to it), but need not be at the root of the template-dir.

        If supplied, `filter` must be a callable taking a single string
        argument. It will be called for every file before processing it, with
        the file name (relative to root of the tree) as the argument. If filter
        returns a non-empty string, file will be rendered. If it returns None
        or an empty string, file will be skipped. If `filter` is not defined,
        all files are processed.

        In the returned structure, `file_name` is location of the file
        relative to the tree root (unless changed by `filter`) and
        `contents` is file contents rendered to a binary (utf8-encoded) string.

        Directories are implied by file paths, not represented by elements
        in the returned dictionary.
        """

        retval = {}

        # Actual full path of the root of the tree we're rendering
        full_root = join(self.template_dir, root)

        for path, subdirs, files in walk(full_root):
            for file in files:
                file_path = join(path, file)  # actual full path of the template file
                output_location = Path(file_path).relative_to(full_root).as_posix()  # template relative to tree root

                # Skip .DS_Store files
                if file == ".DS_Store":
                    continue
                elif file.endswith(
                    (".png", ".jpg", ".jpeg", ".gif", ".ico", ".svg", ".woff", ".woff2", ".ttf", ".eot")
                ):
                    with open(file_path, "rb") as f:
                        content = f.read()
                        final_path = join(full_root_dir, output_location)
                        os.makedirs(os.path.dirname(final_path), exist_ok=True)
                        with open(final_path, "wb") as out:
                            out.write(content)
                    continue

                tpl_location = relpath(file_path, self.template_dir)  # template relative to template_dir

                if filter:
                    output_location = filter(output_location)
                    if not output_location:
                        continue

                contents = self.render_template(tpl_location, context)
                if contents != "":
                    retval[output_location] = contents

        return retval
