"""
Configuration Django — frontend NDB SHOPPING.

Ce projet ne stocke aucune donnée métier. L'authentification Django classique
(django.contrib.auth) n'est PAS utilisée : les utilisateurs, produits et
commandes vivent dans l'API Spring Boot. La session Django ne sert qu'à
conserver le JWT, le rôle, et le panier invité.
"""
import os
from pathlib import Path

from django.contrib.messages import constants as message_constants
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "changeme-in-production")
DEBUG = os.environ.get("DJANGO_DEBUG", "False") == "True"

ALLOWED_HOSTS = [
    h.strip()
    for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if h.strip()
]

# Appelé côté serveur (Django parle au backend via le réseau Docker interne).
API_BASE_URL = os.environ.get("API_BASE_URL", "http://backend:8080/api")

# Utilisé dans les templates pour construire les URLs d'images (/media/...).
MEDIA_BACKEND_URL = os.environ.get("MEDIA_BACKEND_URL", "http://localhost:8085/media")

# Utilisé UNIQUEMENT côté client (JS navigateur) pour le WebSocket STOMP.
# Doit être un hôte PUBLIC (ex: ndbshopping.duckdns.org), pas le nom du conteneur.
PUBLIC_BACKEND_HOST = os.environ.get("PUBLIC_BACKEND_HOST", "localhost:8085")

INSTALLED_APPS = [
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "core",
    "catalog",
    "cart",
    "accounts",
    "adminpanel",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "core.middleware.ApiAuthMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.template.context_processors.i18n",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.storefront",
                "core.context_processors.admin_badges",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# SQLite présent uniquement pour que Django démarre. Aucune table métier.
# Les sessions sont des cookies signés (pas de table django_session).
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.signed_cookies"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# En local HTTP : DJANGO_COOKIE_SECURE=False. En prod HTTPS : True.
SESSION_COOKIE_SECURE = os.environ.get("DJANGO_COOKIE_SECURE", "False") == "True"
CSRF_COOKIE_SECURE = SESSION_COOKIE_SECURE
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # 14 jours

# i18n : uniquement les textes FIXES de l'interface (menus, boutons, labels,
# messages). Le contenu métier saisi par l'admin (noms de produits, descriptions,
# titres de publications, noms de catégories) n'est PAS traduit — il s'affiche
# tel quel, dans la langue où il a été écrit. Ce n'est pas un bug.
LANGUAGE_CODE = "fr"
LANGUAGES = [
    ("fr", "Français"),
    ("ar", "العربية"),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Africa/Nouakchott"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CSRF_TRUSTED_ORIGINS = [
    o.strip()
    for o in os.environ.get(
        "DJANGO_CSRF_TRUSTED_ORIGINS",
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if o.strip()
]

# Derrière Nginx (X-Forwarded-Proto: https)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

MESSAGE_STORAGE = "django.contrib.messages.storage.session.SessionStorage"

MESSAGE_TAGS = {
    message_constants.DEBUG: "secondary",
    message_constants.INFO: "info",
    message_constants.SUCCESS: "success",
    message_constants.WARNING: "warning",
    message_constants.ERROR: "danger",
}

API_TIMEOUT = int(os.environ.get("API_TIMEOUT", "15"))

# En production (DEBUG=False), Django n'envoie les erreurs qu'à mail_admins par défaut :
# rien n'apparaît dans `docker logs`. On force la console (stdout du conteneur).
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "{levelname} {asctime} {name} {message}",
            "style": "{",
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
        "services.api_client": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "core.views": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "core.context_processors": {"level": "ERROR", "handlers": ["console"], "propagate": False},
        "django.request": {"level": "ERROR", "handlers": ["console"], "propagate": False},
    },
}
