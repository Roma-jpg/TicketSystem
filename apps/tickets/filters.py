import django_filters
from django import forms
from django.db import models
from .models import Ticket


class TicketFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(
        method='filter_search',
        label='Поиск',
        widget=forms.TextInput(attrs={'placeholder': 'Номер, кабинет, инв. номер...'})
    )
    created_after = django_filters.DateFilter(
        field_name='created_at', lookup_expr='gte',
        label='Создана после',
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    created_before = django_filters.DateFilter(
        field_name='created_at', lookup_expr='lte',
        label='Создана до',
        widget=forms.DateInput(attrs={'type': 'date'})
    )

    class Meta:
        model = Ticket
        fields = ['status', 'urgency', 'category', 'room_number', 'assigned_to']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            models.Q(ticket_number__icontains=value) |
            models.Q(room_number__icontains=value) |
            models.Q(device_asset_tag__icontains=value) |
            models.Q(description__icontains=value)
        )