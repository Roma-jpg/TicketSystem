from django.urls import path
from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="ticket_list"),
    path("create/", views.ticket_create, name="ticket_create"),
    path("<uuid:pk>/", views.ticket_detail, name="ticket_detail"),
]