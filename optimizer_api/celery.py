
import environ
import os

# Load .env explicitly
env = environ.Env()
environ.Env.read_env()

from celery import Celery
from django.conf import settings
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "optimizer_api.settings")
django.setup()

app = Celery("optimizer_api")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()





