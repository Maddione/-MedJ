from __future__ import annotations

import os
import sys


def main() -> None:
    """Entrypoint for manage.py commands."""
    os.environ.setdefault(
        "DJANGO_SETTINGS_MODULE",
        os.getenv("DJANGO_SETTINGS_MODULE", "settings"),
    )

    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Is it installed and is your virtualenv active?"
        ) from exc

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()

