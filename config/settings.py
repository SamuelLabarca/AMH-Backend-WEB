"""
Configuración de la API del portal de pagos.

Todo lo que cambia entre entornos (claves, base de datos, correo,
orígenes permitidos) sale de variables de entorno, cargadas desde `.env`
en desarrollo. Ver `.env.example`.
"""

import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def lista(nombre, defecto=""):
    """Variable de entorno separada por comas → lista sin vacíos."""
    return [v.strip() for v in os.environ.get(nombre, defecto).split(",") if v.strip()]


DEBUG = os.environ.get("DEBUG", "false").lower() == "true"

# Sin SECRET_KEY en producción no arranca: una clave por defecto filtrada
# en el repositorio permitiría falsificar sesiones y enlaces de recuperación.
SECRET_KEY = os.environ.get("SECRET_KEY") or ("solo-desarrollo-no-usar-en-produccion" if DEBUG else None)
if not SECRET_KEY:
    raise RuntimeError("Falta SECRET_KEY en el entorno.")

ALLOWED_HOSTS = lista("ALLOWED_HOSTS", "localhost,127.0.0.1")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "cuentas",
    "catalogo",
    "tienda",
    "suscripciones",
    "pagos",
    "notificaciones",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    # Antes de CommonMiddleware: tiene que responder el preflight de CORS.
    "corsheaders.middleware.CorsMiddleware",
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
        "DIRS": [],
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

WSGI_APPLICATION = "config.wsgi.application"

# ---------------------------------------------------------------------------
# BASE DE DATOS
# PostgreSQL con DATABASE_URL. Sin ella, SQLite: así el proyecto arranca y
# los tests corren sin instalar nada. Producción SIEMPRE con PostgreSQL.
# ---------------------------------------------------------------------------
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=60,
    )
}

# ---------------------------------------------------------------------------
# USUARIOS Y CONTRASEÑAS
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "cuentas.Usuario"

# argon2 primero: es el hash de las contraseñas nuevas. El otro solo
# sirve para leer hashes antiguos, si los hubiera.
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

# La misma regla que avisa el frontend: 8 caracteres con letras y números.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "cuentas.validadores.LetrasYNumerosValidator"},
]

# El enlace de recuperación vence a los 30 minutos (en segundos).
PASSWORD_RESET_TIMEOUT = 30 * 60

# ---------------------------------------------------------------------------
# SESIÓN Y CSRF
# La sesión vive en una cookie HttpOnly: JavaScript no puede leerla, así
# que un script inyectado no puede robarla. La de CSRF sí es legible: el
# frontend la copia en la cabecera X-CSRFToken en cada POST/DELETE.
# ---------------------------------------------------------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_AGE = 60 * 60 * 8  # una jornada
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = lista("ORIGENES_FRONTEND", "http://localhost:5173")

# El frontend vive en otro origen (otro puerto en desarrollo, otro
# subdominio en producción): CORS con credenciales, solo para él.
CORS_ALLOWED_ORIGINS = lista("ORIGENES_FRONTEND", "http://localhost:5173")
CORS_ALLOW_CREDENTIALS = True

if not DEBUG:
    SECURE_SSL_REDIRECT = True
    SECURE_HSTS_SECONDS = 60 * 60 * 24 * 30
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["cuentas.autenticacion.SesionConCsrf"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "EXCEPTION_HANDLER": "cuentas.errores.manejar_error",
    # Freno a la fuerza bruta. Cada vista sensible declara su `throttle_scope`.
    "DEFAULT_THROTTLE_RATES": {
        "sesion": "10/min",
        "registro": "10/hour",
        "recuperacion": "5/hour",
        "pagos": "20/hour",
        "ordenes": "30/hour",
    },
}

# Los límites de intentos se cuentan en la caché. En producción, con
# varias instancias, tiene que ser compartida (Redis); la de memoria
# local solo sirve para un proceso.
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

# ---------------------------------------------------------------------------
# CORREO
# En desarrollo (DEBUG=true) cada correo se guarda en la BANDEJA LOCAL y se
# lee en /admin → "Bandeja de correos", con sus enlaces listos para abrir.
# En producción, SMTP de Resend (smtp.resend.com, usuario "resend",
# contraseña = API key) o de Brevo. EMAIL_BACKEND en el .env manda sobre
# las dos (p. ej. el de consola, si alguien lo prefiere).
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.environ.get("EMAIL_BACKEND") or (
    "notificaciones.correo.BandejaLocal" if DEBUG else "django.core.mail.backends.smtp.EmailBackend"
)
EMAIL_HOST = os.environ.get("EMAIL_HOST", "")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "AMH Solutions <no-responder@localhost>")

# Dónde vive el portal: con esto se arma el enlace del correo de recuperación.
URL_PORTAL = os.environ.get("URL_PORTAL", "http://localhost:5173/portal-de-pagos")

# ---------------------------------------------------------------------------
LANGUAGE_CODE = "es-ve"
TIME_ZONE = "America/Caracas"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
