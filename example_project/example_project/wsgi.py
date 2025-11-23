import os
import sys
from pathlib import Path

# CURRENT_DIR = .../example_project/example_project
CURRENT_DIR = Path(__file__).resolve().parent

# PROJECT_DIR = .../example_project
PROJECT_DIR = CURRENT_DIR.parent

# REPO_ROOT = .../ (contains django_fastly, blog, example_project)
REPO_ROOT = PROJECT_DIR.parent

# Make sure repo root is on sys.path so Django can import django_fastly and blog
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
