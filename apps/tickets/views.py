from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from apps.notifications.tasks import send_ticket_created_email

from .forms import TicketAttachmentForm, TicketCommentForm, TicketForm
from .models import Ticket

import logging

logger = logging.getLogger(__name__)

def _can_view_ticket(user, ticket):
    return user.is_it() or ticket.created_by_id == user.id


def _queue_ticket_email(email, ticket_number):
    if not email:
        return
    try:
        send_ticket_created_email.delay(email, ticket_number)
    except Exception:
        # Celery (or Redis) is not available – log and do not block the user.
        logger.warning(
            "Could not queue email for ticket %s. Celery broker may be down.",
            ticket_number,
        )
@login_required
def ticket_list(request):
    tickets = Ticket.objects.select_related("created_by", "assigned_to").prefetch_related(
        "comments", "attachments", "history"
    )
    if not request.user.is_it():
        tickets = tickets.filter(created_by=request.user)
    return render(request, "tickets/list.html", {"tickets": tickets})


@login_required
def ticket_create(request):
    if request.method == "POST":
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()
            _queue_ticket_email(ticket.created_by.email, ticket.ticket_number)
            messages.success(request, f"Заявка {ticket.ticket_number} создана.")
            return redirect("tickets:ticket_detail", pk=ticket.pk)
    else:
        form = TicketForm()
    return render(request, "tickets/create.html", {"form": form})


@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(
        Ticket.objects.select_related("created_by", "assigned_to").prefetch_related(
            "comments__author", "attachments__uploaded_by", "history__changed_by"
        ),
        pk=pk,
    )
    if not _can_view_ticket(request.user, ticket):
        return redirect("home")

    comment_form = TicketCommentForm()
    attachment_form = TicketAttachmentForm()

    if request.method == "POST":
        action = request.POST.get("action")
        if action == "comment":
            comment_form = TicketCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.ticket = ticket
                comment.author = request.user
                comment.save()
                messages.success(request, "Комментарий добавлен.")
                return redirect("tickets:ticket_detail", pk=ticket.pk)
        elif action == "attachment":
            attachment_form = TicketAttachmentForm(request.POST, request.FILES)
            if attachment_form.is_valid():
                attachment = attachment_form.save(commit=False)
                attachment.ticket = ticket
                attachment.uploaded_by = request.user
                attachment.save()
                messages.success(request, "Вложение добавлено.")
                return redirect("tickets:ticket_detail", pk=ticket.pk)

    return render(request, "tickets/detail.html", {
        "ticket": ticket,
        "comment_form": comment_form,
        "attachment_form": attachment_form,
    })