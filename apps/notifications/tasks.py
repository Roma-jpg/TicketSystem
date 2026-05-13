# apps/notifications/tasks.py
from celery import shared_task
from django.core.mail import send_mail
from django.contrib.auth import get_user_model

User = get_user_model()


@shared_task
def send_ticket_created_email(email, ticket_number):
    send_mail(
        subject=f"Заявка создана {ticket_number}",
        message=f"Ваша заявка {ticket_number} была создана.",
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )


@shared_task
def send_status_change_email(recipient_ids, ticket_number, old_status, new_status):
    """Send email to all relevant users when a ticket status changes."""
    emails = list(
        User.objects.filter(id__in=recipient_ids, is_active=True)
        .values_list("email", flat=True)
    )
    if not emails:
        return
    send_mail(
        subject=f"Статус заявки {ticket_number} изменён",
        message=f"Заявка {ticket_number}: статус изменён с {old_status} на {new_status}.",
        from_email=None,
        recipient_list=emails,
        fail_silently=False,
    )