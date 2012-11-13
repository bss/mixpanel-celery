DEBUG = True

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    },
}

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
    },
}

INSTALLED_APPS = (
    'djcelery',
    'mixpanel',
)

import djcelery
djcelery.setup_loader()

CELERY_ALWAYS_EAGER = True
CELERY_EAGER_PROPAGATES_EXCEPTIONS = True
CELERY_RESULT_BACKEND = 'cache'
CELERY_CACHE_BACKEND = 'default'
SEND_CELERY_TASK_ERROR_EMAILS = False

MIXPANEL_API_TOKEN = 'testmixpanel'
