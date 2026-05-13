from django.urls import path
from . import views

app_name = "tickets"

urlpatterns = [
    path("", views.ticket_list, name="ticket_list"),
    path("create/", views.ticket_create, name="ticket_create"),
    path("guest/", views.guest_ticket_create, name="guest_ticket_create"),
    path("<uuid:pk>/", views.ticket_detail, name="ticket_detail"),
    path("<uuid:pk>/delete/", views.ticket_delete, name="ticket_delete"),
    path("guest/<uuid:pk>/", views.guest_ticket_detail, name="guest_ticket_detail"),
]
