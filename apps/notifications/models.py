# apps/notifications/models.py
from django.conf import settings
from django.db import models


class Notification(models.Model):
    class Type(models.TextChoices):
        STATUS_CHANGE = "status_change", "Изменение статуса"
        COMMENT = "comment", "Новый комментарий"

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    ticket = models.ForeignKey(
        "tickets.Ticket",
        on_delete=models.CASCADE,
        related_name="notifications",
    )
    notification_type = models.CharField(
        max_length=20,
        choices=Type.choices,
    )
    message = models.CharField(max_length=500)
    read = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    triggered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="triggered_notifications",
    )

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "read"]),
        ]

    def __str__(self):
        return f"Notify {self.recipient}: {self.message[:50]}"