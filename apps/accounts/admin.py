from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    model = User
    list_display = ("username", "email", "role", "room", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active", "groups")
    search_fields = ("username", "email", "room")
    ordering = ("username",)

    fieldsets = UserAdmin.fieldsets + (
        ("Дополнительно", {"fields": ("role", "room")}),
    )

    add_fieldsets = UserAdmin.add_fieldsets + (
        ("Дополнительно", {"fields": ("role", "room")}),
    )