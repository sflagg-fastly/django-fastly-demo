import os
from pathlib import Path
import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = "django-fastly-demo-secret-key"
DEBUG = False
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django_fastly",
    "blog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "example_project.middleware.BlockDangerousQueryParamsMiddleware", 
    "django_fastly.middleware.FastlySurrogateKeyMiddleware",
    "django_fastly.middleware.FastlyCorsEdgeModuleMiddleware",
]

ROOT_URLCONF = "example_project.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "blog" / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "example_project.wsgi.application"

DATABASE_URL = os.environ.get("DATABASE_URL")

if DATABASE_URL:
    # Render / production: use Postgres from DATABASE_URL, require SSL
    DATABASES = {
        "default": dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600,
            ssl_require=True,
        )
    }
else:
    # Local dev / no DATABASE_URL: fall back to SQLite
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }



AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "static"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

FASTLY = {}

CSRF_TRUSTED_ORIGINS = [
    "https://django-fastly-demo.onrender.com",
    "https://django-fastly-demo.global.ssl.fastly.net",
    # If you later add a custom CNAME, put it here too, e.g.:
    # "https://admin.yourdomain.com"
]

ALLOWED_HOSTS = [
    # Local dev
    "127.0.0.1",
    "localhost",
    "0.0.0.0",

    # Deployed hosts
    "django-fastly-demo.onrender.com",
    "django-fastly-demo.global.ssl.fastly.net",
    
]

SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
