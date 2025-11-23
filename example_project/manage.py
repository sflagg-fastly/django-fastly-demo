#!/usr/bin/env python
import os
import sys
from pathlib import Path

# BASE_DIR = example_project/ (where manage.py lives)
BASE_DIR = Path(__file__).resolve().parent

# PROJECT_ROOT = django-fastly-demo/ (one level up)
PROJECT_ROOT = BASE_DIR.parent

# Make sure the repo root is on sys.path so we can import `django_fastly` and `blog`
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def main():
    # Inner Django project package: example_project/example_project/settings.py
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")
    from django.core.management import execute_from_command_line
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
