import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env()
env.read_env(BASE_DIR / ".env")

from celery import Celery
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "optimizer_api.settings")
django.setup()

app = Celery("optimizer_api")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()




