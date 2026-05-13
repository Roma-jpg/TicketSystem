from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from apps.tickets import views as ticket_views

urlpatterns = [
    path("", ticket_views.ticket_list, name="home"),
    path("admin/", admin.site.urls),
    path("accounts/", include("django.contrib.auth.urls")),
    path("tickets/", include(("apps.tickets.urls", "tickets"), namespace="tickets")),
    path("notifications/", include("apps.notifications.urls", namespace="notifications")),
    path("analytics/", include("apps.analytics.urls", namespace="analytics")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)