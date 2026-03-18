"""
Django settings for buspass project.
"""
import os
import dj_database_url
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-buspass-college-app-secret-key-2024')

# Always False in production; override locally via .env DEBUG=True
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = ['*', '.railway.app']

# Railway sits behind a TLS-terminating proxy – tell Django to trust the
# X-Forwarded-Proto header so it recognises requests as HTTPS.  Without this
# the CSRF middleware sees scheme = 'http' and rejects the cookie (403).
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Include wildcard subdomains so preview deployments (*.up.railway.app)
# and the main production URL all pass CSRF validation.
CSRF_TRUSTED_ORIGINS = [
    'https://*.railway.app',
    'https://*.up.railway.app',
]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # Prevents browser from caching authenticated pages (fixes Back-button session leak)
    'core.middleware.NoCacheAuthMiddleware',
]

ROOT_URLCONF = 'buspass.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'buspass.wsgi.application'

# ─── Database ────────────────────────────────────────────────────────────────
# On Railway, DATABASE_URL is injected automatically by the Postgres plugin.
# Locally, fall back to SQLite so zero-config dev still works.
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get(
            'DATABASE_URL',
            'sqlite:///' + str(BASE_DIR / 'buspass_dev.sqlite3'),
        ),
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# ─── Static Files (WhiteNoise) ───────────────────────────────────────────────
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_DIRS = []
STATICFILES_FINDERS = [
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedStaticFilesStorage'
WHITENOISE_USE_FINDERS = DEBUG

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ─── Auth Redirects ──────────────────────────────────────────────────────────
LOGIN_URL = '/login/'
# After login, Dayscholars and all students land on their dashboard
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# ─── External Links ──────────────────────────────────────────────────────────
PAYMENT_LINK = config('PAYMENT_LINK', default='https://razorpay.me/buspass-college')

# ─── Registration Time Window (IST 24h) ─────────────────────────────────────
REGISTRATION_START_HOUR = 9    # 9:00 AM
REGISTRATION_START_MINUTE = 0
REGISTRATION_END_HOUR = 15     # 3:10 PM
REGISTRATION_END_MINUTE = 10

# Bypass date: set to 'YYYY-MM-DD' to allow booking all day (ignores time & Sunday restriction)
# Set to None to re-enable normal restrictions
REGISTRATION_BYPASS_DATE = None

# ─── Bus Pass Fare ───────────────────────────────────────────────────────────
DEFAULT_BUS_FARE = 500

# ─── Session / Cookie Security ──────────────────────────────────────────────
SESSION_COOKIE_AGE = 28800            # 8 hours in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = True   # destroy session when browser closes
SESSION_SAVE_EVERY_REQUEST = False    # only save when modified (performance)
SESSION_COOKIE_HTTPONLY = True        # block JS access to session cookie
SESSION_COOKIE_SAMESITE = 'Lax'      # CSRF mitigation
# Activate HTTPS-only flags in production (Railway always serves over HTTPS)
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = False  # Railway's proxy already enforces HTTPS
# ─── IMPORTANT ───────────────────────────────────────────────────────────────
# Set a real SECRET_KEY in the Railway environment variables panel.
# Generate one with:  python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
