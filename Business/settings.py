"""
BusinessOS - Django settings.

Everything environment specific is read from environment variables
(see .env.example). Sensible defaults keep local development and the
CI test-suite working without any configuration.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


def env_bool(name, default=False):
    return os.getenv(name, str(default)).strip().lower() in ("1", "true", "yes", "on")


def env_list(name, default=""):
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
DEBUG = env_bool("DEBUG", True)

SECRET_KEY = os.getenv("SECRET_KEY", "")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "django-insecure-dev-only-change-me"
    else:
        raise RuntimeError("SECRET_KEY environment variable is required when DEBUG is False.")

ALLOWED_HOSTS = env_list("ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0,testserver")
CSRF_TRUSTED_ORIGINS = env_list("CSRF_TRUSTED_ORIGINS")

# Render sets this automatically (e.g. myapp.onrender.com)
_render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME")
if _render_host:
    ALLOWED_HOSTS.append(_render_host)
    CSRF_TRUSTED_ORIGINS.append(f"https://{_render_host}")

AUTH_USER_MODEL = "accounts.User"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third party
    "rest_framework",
    "rest_framework.authtoken",
    "rest_framework_simplejwt",
    "django_filters",
    "drf_spectacular",
    "corsheaders",
    # project apps
    "common",
    "apps.accounts",
    "apps.organizations",
    "apps.products",
    "apps.inventory",
    "apps.customers",
    "apps.orders",
    "apps.expenses",
    "apps.payments",
    "apps.invoices",
    "apps.notifications",
    "apps.analytics",
    "apps.ai",
    "api",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

if not DEBUG:
    # Serve collected static files straight from gunicorn (no nginx needed).
    MIDDLEWARE.insert(2, "whitenoise.middleware.WhiteNoiseMiddleware")

ROOT_URLCONF = "Business.urls"

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
                "common.context_processors.sidebar_counts",
            ],
        },
    },
]

WSGI_APPLICATION = "Business.wsgi.application"
ASGI_APPLICATION = "Business.asgi.application"

SESSION_COOKIE_AGE = int(os.getenv("SESSION_COOKIE_AGE", 1800))
SESSION_EXPIRE_AT_BROWSER_CLOSE = True


# ---------------------------------------------------------------------------
# Database: PostgreSQL via DATABASE_URL, MySQL via DB_HOST, otherwise SQLite.
# ---------------------------------------------------------------------------

if os.getenv("DATABASE_URL"):
    # PostgreSQL via DATABASE_URL
    import dj_database_url

    DATABASES = {
        "default": dj_database_url.parse(
            os.environ["DATABASE_URL"],
            conn_max_age=600,
            conn_health_checks=True,
        )
    }

elif os.getenv("DB_HOST"):
    # MySQL: prefer mysqlclient, otherwise use PyMySQL
    try:
        import MySQLdb  # noqa: F401
    except ImportError:
        import pymysql

        pymysql.version_info = (2, 2, 1, "final", 0)
        pymysql.install_as_MySQLdb()

    _mysql_options = {
        "charset": "utf8mb4",
    }

    # Aiven MySQL SSL certificate verification
    db_ssl_ca = os.getenv("DB_SSL_CA", "").strip()

    if db_ssl_ca:
        _mysql_options["ssl"] = {
            "ca": db_ssl_ca,
            "check_hostname": True,
        }

    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": os.getenv("DB_NAME", "businessos"),
            "USER": os.getenv("DB_USER", "businessos"),
            "PASSWORD": os.getenv("DB_PASSWORD", ""),
            "HOST": os.getenv("DB_HOST"),
            "PORT": os.getenv("DB_PORT", "3306"),
            "CONN_MAX_AGE": int(os.getenv("DB_CONN_MAX_AGE", "60")),
            "CONN_HEALTH_CHECKS": True,
            "OPTIONS": _mysql_options,
        }
    }

else:
    # Local development / CI fallback
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / os.getenv("SQLITE_NAME", "db.sqlite3"),
        }
    }

# ---------------------------------------------------------------------------
# Email (password reset). Console backend in development, SMTP when EMAIL_HOST is set.
# ---------------------------------------------------------------------------
if os.getenv("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
    EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "BusinessOS <no-reply@businessos.local>")
PASSWORD_RESET_TIMEOUT = int(os.getenv("PASSWORD_RESET_TIMEOUT", 3600))  # seconds

# ---------------------------------------------------------------------------
# i18n
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "Asia/Kolkata")
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static files (master.css / master.js live in /static)
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": (
            "django.contrib.staticfiles.storage.StaticFilesStorage"
            if DEBUG
            else "whitenoise.storage.CompressedManifestStaticFilesStorage"
        )
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login/"
LOGIN_REDIRECT_URL = "/dashboard/"
LOGOUT_REDIRECT_URL = "/"

# ---------------------------------------------------------------------------
# Django REST Framework + JWT + OpenAPI docs
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.UserRateThrottle",
        "rest_framework.throttling.AnonRateThrottle",
    ],
    "EXCEPTION_HANDLER": "api.exception_handler.custom_exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        "user": os.getenv("THROTTLE_USER", "1000/minute"),
        "anon": os.getenv("THROTTLE_ANON", "60/minute"),
        "product": "120/minute",
        "customer": "120/minute",
        "expense": "120/minute",
        "inventory": "120/minute",
        "invoice": "120/minute",
        "notification": "120/minute",
        "order": "120/minute",
        "organisation": "60/minute",
        "payment": "120/minute",
        "account": "60/minute",
        "login": "30/minute",
        "dashboard": "60/minute",
        "forecast": "60/minute",
    },
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", 30))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.getenv("JWT_REFRESH_DAYS", 7))),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "BusinessOS API",
    "DESCRIPTION": "Business management API built with Django REST Framework",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "OrderStatusEnum": "apps.orders.models.Order.Status",
        "InvoiceStatusEnum": "apps.invoices.models.Invoice.Status",
        "PaymentStatusEnum": "apps.payments.models.Payment.Status",
    },
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = env_list(
    "CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000"
)

# ---------------------------------------------------------------------------
# Production hardening (only when DEBUG is off)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", False)
    SESSION_COOKIE_SECURE = env_bool("SESSION_COOKIE_SECURE", False)
    CSRF_COOKIE_SECURE = env_bool("CSRF_COOKIE_SECURE", False)
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": os.getenv("LOG_LEVEL", "INFO")},
}
