# Hesperia output_views — Django settings (site builder / HTML previews).
# Copyright © 2026 igareosh.com. See Hesperia LEGAL_NOTICE.md.
# Ref: brain repo governance/SPEC-ETHAN-HESPERIA-DJANGO-OUTPUT-VIEWS.md

from pathlib import Path

import environ

# output_views/ (this Django project root)
BASE_DIR = Path(__file__).resolve().parent.parent.parent
# Hesperia engine repo root (parent of output_views/)
HESPERIA_ROOT = BASE_DIR.parent

env = environ.Env()
environ.Env.read_env(HESPERIA_ROOT / ".env", overwrite=False)

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-dev-only-set-DJANGO_SECRET_KEY-in-prod")
DEBUG = env.bool("DJANGO_DEBUG", default=True)
ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["hesperia.prichindel.com", "127.0.0.1", "localhost", "[::1]"],
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "apps.pages",
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
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "config.context_processors.django_version",
            ],
        },
    },
]

LOCAL_DIR = BASE_DIR / ".local"
LOCAL_DIR.mkdir(parents=True, exist_ok=True)

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": LOCAL_DIR / "db.sqlite3",
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"] if (BASE_DIR / "static").is_dir() else []
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # No manifest file required (unlike CompressedManifestStaticFilesStorage).
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Prod security — nginx terminates TLS; Django trusts X-Forwarded-Proto from localhost proxy.
# Not setting SECURE_SSL_REDIRECT: nginx handles HTTP→HTTPS redirect, Django runs on 127.0.0.1 only.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_HSTS_SECONDS = env.int("DJANGO_HSTS_SECONDS", default=0 if DEBUG else 31536000)
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_HSTS_PRELOAD = not DEBUG
SECURE_CONTENT_TYPE_NOSNIFF = True
# W008 is intentional: nginx handles HTTP→HTTPS; Django runs on loopback only.
SILENCED_SYSTEM_CHECKS = ["security.W008"]

# Operator / client preview: optional FastAPI JSON API base (Phase B HTTP bridge)
HESPERIA_FASTAPI_ANALYZE_URL = env("HESPERIA_FASTAPI_ANALYZE_URL", default="")
