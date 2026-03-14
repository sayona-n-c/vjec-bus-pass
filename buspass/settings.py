"""
Django settings for buspass project.
"""
import os
from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY', default='django-insecure-buspass-college-app-secret-key-2024')

DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://web-production-52466.up.railway.app',
    cast=Csv()
)

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

# Database – MySQL when password is configured, SQLite fallback for zero-config dev
_db_password = config('DB_PASSWORD', default='')
_use_mysql    = config('USE_MYSQL', default='auto')

if _use_mysql == 'true' or (_use_mysql == 'auto' and _db_password):
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': config('DB_NAME', default='buspass_db'),
            'USER': config('DB_USER', default='root'),
            'PASSWORD': _db_password,
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='3306'),
            'OPTIONS': {
                'charset': 'utf8mb4',
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            },
        }
    }
else:
    # SQLite – works out-of-the-box, great for development
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'buspass_dev.sqlite3',
        }
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

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

# External payment link
PAYMENT_LINK = config('PAYMENT_LINK', default='https://razorpay.me/buspass-college')

# Registration time window (IST 24h)
REGISTRATION_START_HOUR = 9   # 9:00 AM
REGISTRATION_START_MINUTE = 0
REGISTRATION_END_HOUR = 15    # 3:10 PM
REGISTRATION_END_MINUTE = 10

# Bus pass fare
DEFAULT_BUS_FARE = 500

# ─ Session Security ─────────────────────────────────────────────────────
SESSION_COOKIE_AGE = 28800           # 8 hours in seconds
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # destroy session when browser closes
SESSION_SAVE_EVERY_REQUEST = False   # only save when modified (performance)
SESSION_COOKIE_HTTPONLY = True       # block JS access to session cookie
SESSION_COOKIE_SAMESITE = 'Lax'     # CSRF mitigation
