# TicketSystem141

Django-based IT ticketing system with:

- custom accounts and roles
- ticket creation and detail pages
- comments and attachments
- audit history
- websocket real‑time notifications
- Celery email alerts

## Setup

### Option 1 - local SQLite
1. Copy `.env.example` to `.env`
2. Keep `USE_SQLITE=True`
3. Install dependencies: `pip install -r requirements.txt`
4. Run migrations: `python manage.py migrate`
5. Create superuser: `python manage.py createsuperuser`
6. Run the app: `python manage.py runserver`

### Option 2 - Docker
1. Copy `.env.example` to `.env`
2. Set:
   - `USE_SQLITE=False`
   - `POSTGRES_HOST=db`
   - `REDIS_URL=redis://redis:6379/0`
   - `CELERY_BROKER_URL=redis://redis:6379/0`
   - `CELERY_RESULT_BACKEND=redis://redis:6379/0`
3. Start everything: `docker compose up --build`

## Important URLs
- `/` - ticket dashboard
- `/tickets/` - ticket list
- `/tickets/create/` - create a ticket
- `/accounts/login/` - login
- `/admin/` - Django admin

## Notes
- Redis is required for WebSocket broadcasts and Celery.
- File uploads are stored in `media/`.
````

### Main project folder (`TicketSystem141/`)

#### `TicketSystem141/settings.py` (replace)
```python
"""
Django settings for TicketSystem141 project.
"""

from pathlib import Path

import dj_database_url
from decouple import config


BASE_DIR = Path(__file__).resolve().parent.parent


def split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


SECRET_KEY = config("SECRET_KEY", default="django-insecure-change-me")
DEBUG = config("DEBUG", default=False, cast=bool)
ALLOWED_HOSTS = split_csv(
    config("ALLOWED_HOSTS", default="localhost,127.0.0.1,0.0.0.0")
)
CSRF_TRUSTED_ORIGINS = split_csv(config("CSRF_TRUSTED_ORIGINS", default=""))


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "daphne",
    "rest_framework",
    "channels",
    "django_filters",
    "apps.accounts.apps.AccountsConfig",
    "apps.tickets.apps.TicketsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.configpanel.apps.ConfigpanelConfig",
    "apps.auditlogs.apps.AuditlogsConfig",
    "apps.assets.apps.AssetsConfig",
    "apps.common.apps.CommonConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "TicketSystem141.urls"

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
            ],
        },
    },
]

WSGI_APPLICATION = "TicketSystem141.wsgi.application"
ASGI_APPLICATION = "TicketSystem141.asgi.application"

USE_SQLITE = config("USE_SQLITE", default=True, cast=bool)
DATABASE_URL = config("DATABASE_URL", default="")

if USE_SQLITE:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }
elif DATABASE_URL:
    DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": config("POSTGRES_DB", default="ticketing_db"),
            "USER": config("POSTGRES_USER", default="postgres"),
            "PASSWORD": config("POSTGRES_PASSWORD", default="postgres"),
            "HOST": config("POSTGRES_HOST", default="localhost"),
            "PORT": config("POSTGRES_PORT", default="5432"),
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = config("TIME_ZONE", default="UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

REDIS_URL = config("REDIS_URL", default="redis://127.0.0.1:6379/0")

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    },
}

CELERY_BROKER_URL = config("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = config("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE

EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@tickets.local")
EMAIL_HOST = config("EMAIL_HOST", default="localhost")
EMAIL_PORT = config("EMAIL_PORT", default=25, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=False, cast=bool)
EMAIL_USE_SSL = config("EMAIL_USE_SSL", default=False, cast=bool)