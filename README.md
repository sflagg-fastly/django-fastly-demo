# django-fastly-demo

Minimal Django project that demonstrates a Fastly integration package
plus a simple blog app for testing.

## Quick start

```bash
cd example_project
python -m venv .venv
source .venv/bin/activate
pip install -r ../requirements.txt  # or install Django + requests manually
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Then visit `/admin/` to configure Fastly and `/` to see the blog.
