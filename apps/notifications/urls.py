from django.urls import path
from . import views

app_name = "notifications"

urlpatterns = [
    path("api/list/", views.notification_list_api, name="notification_list_api"),
    path("api/mark-read/<int:pk>/", views.mark_notification_read, name="mark_notification_read"),
]