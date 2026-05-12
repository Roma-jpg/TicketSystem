import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


class Ticket(models.Model):

    class DeviceTypes(models.TextChoices):
        DESKTOP = "desktop", "Настольный компьютер"
        LAPTOP = "laptop", "Ноутбук"
        CHROMEBOOK = "chromebook", "Хромбук"
        PROJECTOR = "projector", "Проектор"
        PRINTER = "printer", "Принтер"
        OTHER = "other", "Другое"

    class Categories(models.TextChoices):
        HARDWARE = "hardware", "Оборудование"
        SOFTWARE = "software", "Программное обеспечение"
        NETWORK = "network", "Сеть"
        PERIPHERALS = "peripherals", "Периферия"
        OTHER = "other", "Другое"

    class Status(models.TextChoices):
        OPEN = "open", "Открыта"
        ACKNOWLEDGED = "acknowledged", "Подтверждена"
        ASSIGNED = "assigned", "Назначена"
        IN_PROGRESS = "in_progress", "В работе"
        WAITING_PARTS = "waiting_parts", "Ожидание запчастей"
        WAITING_USER = "waiting_user", "Ожидание пользователя"
        RESOLVED = "resolved", "Решена"
        CLOSED = "closed", "Закрыта"
        REOPENED = "reopened", "Переоткрыта"
        DUPLICATE = "duplicate", "Дубликат"

    class Urgency(models.TextChoices):
        LOW = "low", "Низкая"
        MEDIUM = "medium", "Средняя"
        HIGH = "high", "Высокая"

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )

    ticket_number = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_tickets",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_tickets",
    )

    room_number = models.CharField(
        max_length=32,
        db_index=True,
    )

    device_type = models.CharField(
        max_length=32,
        choices=DeviceTypes.choices,
    )

    device_asset_tag = models.CharField(
        max_length=128,
        blank=True,
    )

    category = models.CharField(
        max_length=32,
        choices=Categories.choices,
        db_index=True,
    )

    urgency = models.CharField(
        max_length=16,
        choices=Urgency.choices,
        db_index=True,
    )

    description = models.TextField()

    status = models.CharField(
        max_length=32,
        choices=Status.choices,
        default=Status.OPEN,
        db_index=True,
    )

    is_overdue = models.BooleanField(
        default=False,
        db_index=True,
    )

    merged_into = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "urgency"]),
            models.Index(fields=["room_number"]),
            models.Index(fields=["created_at"]),
        ]

    def save(self, *args, **kwargs):

        if not self.ticket_number:
            date_str = timezone.now().strftime("%Y%m%d")
            count = Ticket.objects.count() + 1
            self.ticket_number = f"IT-{date_str}-{count:04}"

        super().save(*args, **kwargs)

    def __str__(self):
        return self.ticket_number


class TicketAttachment(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="attachments",
    )

    file = models.FileField(
        upload_to="ticket_attachments/"
    )

    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Вложение к {self.ticket.ticket_number}"

# 6. Comments + Internal Notes

class TicketComment(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="comments",
    )

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )

    comment = models.TextField()

    internal = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self):
        return f"Комментарий к {self.ticket.ticket_number}"

# 7. Ticket History / Audit

class TicketHistory(models.Model):

    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name="history",
    )

    old_status = models.CharField(
        max_length=32,
        blank=True,
    )

    new_status = models.CharField(
        max_length=32,
    )

    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )

    changed_at = models.DateTimeField(auto_now_add=True)

    note = models.TextField(blank=True)

    class Meta:
        ordering = ["-changed_at"]

    def __str__(self):
        return f"Изменение статуса {self.ticket.ticket_number}"