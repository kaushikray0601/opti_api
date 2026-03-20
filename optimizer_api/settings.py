import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
env.read_env(BASE_DIR / ".env")


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

SECRET_KEY = env('DJANGO_SECRET_KEY')
DEBUG = env.bool("DJANGO_DEBUG", default=env.bool("DEBUG", default=False))
ENV_MODE = env("ENV_MODE", default="dev").strip().lower()
IS_DOCKER = ENV_MODE == "docker"

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=[
        "optimizer_api.local",
        "localhost",
        "127.0.0.1",
        "optimizer-api-web",
        "optimizer-api-nginx",
    ],
)
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])
USE_X_FORWARDED_HOST = env.bool("USE_X_FORWARDED_HOST", default=IS_DOCKER)


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'optimizer',
]

MIDDLEWARE = [    
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'optimizer_api.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'optimizer_api.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

OPTIMIZER_TIME_LIMIT=300  # 5 minutes
OPTIMIZER_API_KEY = env("OPTIMIZER_API_KEY")
CELERY_TASK_ALWAYS_EAGER = env.bool(
    "CELERY_TASK_ALWAYS_EAGER",
    default=DEBUG and not IS_DOCKER,
)

# Celery and Redis settings
if CELERY_TASK_ALWAYS_EAGER:
    CELERY_BROKER_URL = env("CELERY_BROKER_URL_EAGER", default="memory://")
    CELERY_RESULT_BACKEND = env(
        "CELERY_RESULT_BACKEND_EAGER",
        default="cache+memory://",
    )
elif ENV_MODE == "docker":
    CELERY_BROKER_URL = env("CELERY_BROKER_URL_DOCKER")
    CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND_DOCKER")
else:
    CELERY_BROKER_URL = env(
        "CELERY_BROKER_URL_DEV",
        default="redis://localhost:6379/0",
    )
    CELERY_RESULT_BACKEND = env(
        "CELERY_RESULT_BACKEND_DEV",
        default="redis://localhost:6379/0",
    )

CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_TASK_EAGER_PROPAGATES = env.bool(
    "CELERY_TASK_EAGER_PROPAGATES",
    default=CELERY_TASK_ALWAYS_EAGER,
)
CELERY_TASK_STORE_EAGER_RESULT = env.bool(
    "CELERY_TASK_STORE_EAGER_RESULT",
    default=CELERY_TASK_ALWAYS_EAGER,
)

# Add security-related settings for production while keeping local HTTP workable.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
CSRF_COOKIE_SECURE = env.bool(
    "CSRF_COOKIE_SECURE",
    default=not DEBUG and IS_DOCKER,
)
SESSION_COOKIE_SECURE = env.bool(
    "SESSION_COOKIE_SECURE",
    default=not DEBUG and IS_DOCKER,
)
X_FRAME_OPTIONS = 'DENY'

# Logging 
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {'format': '{levelname} {asctime} {module} {message}', 'style': '{'},
        'simple': {'format': '{levelname} {message}', 'style': '{'},
    },
    'handlers': {
        'console': {'class': 'logging.StreamHandler', 'formatter': 'simple'},
    },
    'root': {'handlers': ['console'], 'level': 'INFO'},
}
