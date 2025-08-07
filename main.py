#!/usr/bin/env python


import os.path
import sys

from core.locales.i18n import _, set_locale
set_locale("ru")

try:
    from core.cli.main import run_pythagora
except ImportError as err:
    pythagora_root = os.path.dirname(__file__)
    venv_path = os.path.join(pythagora_root, "venv")
    requirements_path = os.path.join(pythagora_root, "requirements.txt")
    if sys.prefix == sys.base_prefix:
        venv_python_path = os.path.join(venv_path, "scripts" if sys.platform == "win32" else "bin", "python")
        print(_("main.py:python_not_configured", err_name=err.name), file=sys.stderr)
        print(_("main.py:create_virtual_environment", sys_executable=sys.executable, venv_path=venv_path), file=sys.stderr)
        print(
            _("main.py:install_dependencies", venv_python_path=venv_python_path, requirements_path=requirements_path),
            file=sys.stderr,
        )
    else:
        print(
            _("main.py:python_partially_configured", err_name=err.name),
            file=sys.stderr,
        )
        print(
            _("main.py:finish_python_setup", sys_executable=sys.executable, requirements_path=requirements_path),
            file=sys.stderr,
        )
    sys.exit(255)

sys.exit(run_pythagora())
