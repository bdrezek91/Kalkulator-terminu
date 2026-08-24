"""
Ustawienia Django dla Kalkulatora Terminów Pawilonów.

Wszystkie wartości wrażliwe i środowiskowe pochodzą z pliku .env
(patrz .env.example). Nie zapisuj prawdziwych sekretów w repozytorium.
"""

from pathlib import Path

import environ
from django.urls import reverse_lazy

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)
env_file = BASE_DIR / ".env"
if env_file.exists():
    environ.Env.read_env(str(env_file))

SECRET_KEY = env("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-production")
DEBUG = env.bool("DJANGO_DEBUG", default=False)

ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Gdy aplikacja stoi za reverse proxy pod ścieżką inną niż "/" (np. Caddy
# `handle_path /kalkulator-terminu/*` zdejmujący prefiks przed przekazaniem
# żądania dalej) — Django samo tego nie wie i generuje bezwzględne URL-e
# (reverse(), {% url %}, redirect()) od korzenia domeny, co łamie routing na
# współdzielonej domenie (żądanie bez prefiksu trafia do innej aplikacji
# obsługiwanej przez tę samą domenę). FORCE_SCRIPT_NAME dopisuje prefiks do
# wszystkich takich URL-i. STATIC_URL/Whitenoise nie są tym objęte — Caddy
# obsługuje /static/* osobnym blokiem bez zdejmowania prefiksu.
FORCE_SCRIPT_NAME = env("DJANGO_FORCE_SCRIPT_NAME", default=None) or None

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "pawilony",
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

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "pawilony" / "templates"],
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

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://kalkulator:kalkulator@localhost:5432/kalkulator",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        # Manifest (hashed nazw plików) storage jest optymalizacją produkcyjną i wymaga
        # wcześniejszego `collectstatic` — w trybie DEBUG (lokalnie, w testach) serwujemy
        # pliki wprost ze źródła, bez tego wymogu.
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# reverse_lazy (nie twarde stringi) — muszą respektować FORCE_SCRIPT_NAME,
# inaczej po zalogowaniu/wylogowaniu użytkownik trafia poza prefiks ścieżki
# aplikacji na współdzielonej domenie (patrz uwaga przy FORCE_SCRIPT_NAME wyżej).
LOGIN_URL = reverse_lazy("pawilony:login")
LOGIN_REDIRECT_URL = reverse_lazy("pawilony:dashboard")
LOGOUT_REDIRECT_URL = reverse_lazy("pawilony:calculator")

# --- Bezpieczeństwo uploadu ---
IMPORT_MAX_UPLOAD_SIZE_MB = env.int("IMPORT_MAX_UPLOAD_SIZE_MB", default=15)
DATA_UPLOAD_MAX_MEMORY_SIZE = IMPORT_MAX_UPLOAD_SIZE_MB * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = IMPORT_MAX_UPLOAD_SIZE_MB * 1024 * 1024

# Próg (w godzinach), po którym dane uznaje się za nieaktualne na stronie publicznej.
STALE_DATA_WARNING_HOURS_DEFAULT = env.int("STALE_DATA_WARNING_HOURS_DEFAULT", default=24)

# --- Rate limiting publicznego kalkulatora (proste okno czasowe w pamięci cache) ---
CALCULATOR_RATE_LIMIT_COUNT = env.int("CALCULATOR_RATE_LIMIT_COUNT", default=30)
CALCULATOR_RATE_LIMIT_WINDOW_SECONDS = env.int("CALCULATOR_RATE_LIMIT_WINDOW_SECONDS", default=60)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
    }
}

# --- Reverse proxy (Caddy/Nginx) terminujący TLS przed aplikacją ---
# Aplikacja stoi za reverse proxy, który sam obsługuje HTTPS i przekazuje ruch
# dalej po zwykłym HTTP wewnątrz sieci Docker. Bez tego SECURE_SSL_REDIRECT
# wpadłby w nieskończoną pętlę przekierowań, bo Django widziałoby każde
# żądanie jako "niebezpieczne" (http), nawet gdy klient łączył się po https.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# --- Bezpieczeństwo produkcyjne (włączane automatycznie gdy DEBUG=False) ---
if not DEBUG:
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int("DJANGO_SECURE_HSTS_SECONDS", default=3600)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = "DENY"
else:
    SECURE_SSL_REDIRECT = False

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # Django potrzebuje odczytu tokenu CSRF przez JS w formularzach
SECURE_REFERRER_POLICY = "same-origin"

# --- Logowanie działań administracyjnych ---
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "pawilony.audit": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
    },
}
