#!/usr/bin/env python


import os.path
import sys

try:
    from core.cli.main import run_pythagora
except ImportError as err:
    pythagora_root = os.path.dirname(__file__)
    venv_path = os.path.join(pythagora_root, "venv")
    requirements_path = os.path.join(pythagora_root, "requirements.txt")
    if sys.prefix == sys.base_prefix:
        venv_python_path = os.path.join(venv_path, "scripts" if sys.platform == "win32" else "bin", "python")
        print(f"Python environment for Pythagora is not set up: module `{err.name}` is missing.", file=sys.stderr)
        print(f"Please create Python virtual environment: {sys.executable} -m venv {venv_path}", file=sys.stderr)
        print(
            f"Then install the required dependencies with: {venv_python_path} -m pip install -r {requirements_path}",
            file=sys.stderr,
        )
    else:
        print(
            f"Python environment for Pythagora is not completely set up: module `{err.name}` is missing",
            file=sys.stderr,
        )
        print(
            f"Please run `{sys.executable} -m pip install -r {requirements_path}` to finish Python setup, and rerun Pythagora.",
            file=sys.stderr,
        )
    sys.exit(255)

sys.exit(run_pythagora())
