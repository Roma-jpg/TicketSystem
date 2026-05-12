import os

from celery import Celery

os.environ.setdefault(
	"DJANGO_SETTINGS_MODULE",
	"TicketSystem141.settings"
)

app = Celery("TicketSystem141")

app.config_from_object(
	"django.conf:settings",
	namespace="CELERY",
)

app.autodiscover_tasks()