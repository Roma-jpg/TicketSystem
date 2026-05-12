from celery import shared_task
from django.core.mail import send_mail


@shared_task
def send_ticket_created_email(
    email,
    ticket_number,
):

    send_mail(
        subject=f"Заявка создана {ticket_number}",
        message=f"Ваша заявка {ticket_number} была создана.",
        from_email=None,
        recipient_list=[email],
        fail_silently=False,
    )