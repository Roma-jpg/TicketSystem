import logging
import uuid

import os

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect

from apps.accounts.models import User
from apps.notifications.tasks import send_ticket_created_email

from .filters import TicketFilter
from .forms import TicketAttachmentForm, TicketCommentForm, TicketForm, UserAttachmentForm
from .guest_forms import GuestAttachmentForm, GuestTicketForm
from .models import Ticket, TicketAttachment, TicketHistory

logger = logging.getLogger(__name__)


def _can_view_ticket(user, ticket):
    return user.is_it() or user.is_principal() or ticket.created_by_id == user.id


def _queue_ticket_email(email, ticket_number):
    if not email:
        return
    try:
        send_ticket_created_email.delay(email, ticket_number)
    except Exception:
        logger.warning("Could not queue email for ticket %s.", ticket_number)


# ----------------------------------------------------------------------
@login_required
def ticket_list(request):
    """
    Authenticated user sees their own tickets (or all if IT staff).
    Filters and search via django-filter.
    """
    base_qs = Ticket.objects.select_related("created_by", "assigned_to").only(
        "pk", "ticket_number", "status", "urgency", "room_number",
        "created_by__username", "assigned_to__username", "updated_at",
    )
    if not request.user.is_it() and not request.user.is_principal():
        base_qs = base_qs.filter(created_by=request.user)

    # Apply filters on the base queryset (before ordering & pagination)
    ticket_filter = TicketFilter(request.GET, queryset=base_qs)

    paginator = Paginator(ticket_filter.qs.order_by("-created_at"), 25)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "tickets/list.html", {
        "tickets": page_obj,
        "page_obj": page_obj,
        "filter": ticket_filter,   # pass the filter object to template
    })


@login_required
def ticket_create(request):
    # Check if we just created a ticket in the last 30 sec – redirect to it
    last_id = request.session.get('last_created_ticket_id')
    last_time = request.session.get('last_created_time', 0)
    now_ts = timezone.now().timestamp()
    if last_id and (now_ts - last_time < 30):
        del request.session['last_created_ticket_id']
        del request.session['last_created_time']
        return redirect("tickets:ticket_detail", pk=last_id)

    if request.method == "POST":
        form = TicketForm(request.POST, request.FILES)
        attachment_form = UserAttachmentForm(request.POST, request.FILES)
        if form.is_valid() and attachment_form.is_valid():
            ticket = form.save(commit=False)
            ticket.created_by = request.user
            ticket.save()

            files = attachment_form.cleaned_data.get("files", [])
            for f in files:
                TicketAttachment.objects.create(
                    ticket=ticket,
                    file=f,
                    uploaded_by=request.user,
                )

            _queue_ticket_email(ticket.created_by.email, ticket.ticket_number)

            # Store last created ticket in session
            request.session['last_created_ticket_id'] = str(ticket.pk)
            request.session['last_created_time'] = now_ts

            messages.success(request, f"Заявка {ticket.ticket_number} создана.")
            return redirect("tickets:ticket_detail", pk=ticket.pk)
    else:
        form = TicketForm()
        attachment_form = UserAttachmentForm()

    return render(request, "tickets/create.html", {
        "form": form,
        "attachment_form": attachment_form,
    })

# ----------------------------------------------------------------------
def ticket_detail(request, pk):
    queryset = Ticket.objects.select_related("created_by", "assigned_to").prefetch_related(
        "comments__author", "attachments__uploaded_by", "history__changed_by"
    )

    if request.user.is_authenticated:
        ticket = get_object_or_404(queryset, pk=pk)
        if not _can_view_ticket(request.user, ticket):
            return redirect("home")
    else:
        guest_tickets = request.session.get("guest_tickets", [])
        if str(pk) not in guest_tickets:
            return redirect("home")
        ticket = get_object_or_404(queryset, pk=pk)

    all_comments = ticket.comments.all()
    public_comments = [c for c in all_comments if not c.internal]
    # internal comments visible to IT staff and principal (read‑only)
    internal_comments = []
    if request.user.is_authenticated and (request.user.is_it() or request.user.is_principal()):
        internal_comments = [c for c in all_comments if c.internal]

    comment_form = TicketCommentForm()
    attachment_form = TicketAttachmentForm()

    if request.method == "POST":
        action = request.POST.get("action")
        # Helper to decide if request is AJAX
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        if action == "comment" and request.user.is_authenticated:
            comment_form = TicketCommentForm(request.POST)
            if comment_form.is_valid():
                comment = comment_form.save(commit=False)
                comment.ticket = ticket
                comment.author = request.user
                # Only IT staff can mark internal; principal can view but not create internal
                if request.user.is_it():
                    comment.internal = comment_form.cleaned_data.get("internal", False)
                else:
                    comment.internal = False
                comment.save()
                messages.success(request, "Комментарий добавлен.")
                if is_ajax:
                    return JsonResponse({"success": True, "comment_id": comment.id})
                return redirect("tickets:ticket_detail", pk=ticket.pk)
        elif action == "assign" and request.user.is_authenticated and request.user.is_it():
            assign_to_id = request.POST.get("assign_to")
            if assign_to_id:
                try:
                    new_assignee = User.objects.get(pk=assign_to_id)
                except User.DoesNotExist:
                    messages.error(request, "Пользователь не найден.")
                    return redirect("tickets:ticket_detail", pk=ticket.pk)
                # Validate that the target is active IT staff
                if (new_assignee.role not in [User.Roles.IT_STAFF, User.Roles.IT_ADMIN]
                        or not new_assignee.is_active):
                    messages.error(request, "Можно назначить только активного ИТ‑сотрудника.")
                    return redirect("tickets:ticket_detail", pk=ticket.pk)
            else:
                new_assignee = request.user

            old_status = ticket.status
            # Automatically set status to assigned if in an initial state
            if ticket.status in ['open', 'acknowledged', 'reopened']:
                ticket.status = Ticket.Status.ASSIGNED
            ticket.assigned_to = new_assignee

            TicketHistory.objects.create(
                ticket=ticket,
                old_status=old_status,
                new_status=ticket.status,
                changed_by=request.user,
                note=f"Заявка назначена на {new_assignee.username}",
            )
            ticket.save(update_fields=["assigned_to", "status"])
            messages.success(request, f"Заявка назначена на {new_assignee.username}.")
            return redirect("tickets:ticket_detail", pk=ticket.pk)
        elif action == "change_status" and request.user.is_authenticated and request.user.is_it():
            new_status = request.POST.get("new_status")
            if new_status in dict(Ticket.Status.choices):
                old_status = ticket.status
                ticket.status = new_status
                TicketHistory.objects.create(
                    ticket=ticket,
                    old_status=old_status,
                    new_status=new_status,
                    changed_by=request.user,
                    note=f"Статус изменён вручную на {ticket.get_status_display()}",
                )
                ticket.save(update_fields=["status"])
                messages.success(request, f"Статус изменён на {ticket.get_status_display()}.")
            else:
                messages.error(request, "Недопустимый статус.")
            return redirect("tickets:ticket_detail", pk=ticket.pk)
        elif action == "attachment" and request.user.is_authenticated:
            attachment_form = TicketAttachmentForm(request.POST, request.FILES)
            if attachment_form.is_valid():
                attachment = attachment_form.save(commit=False)
                attachment.ticket = ticket
                attachment.uploaded_by = request.user
                attachment.save()
                messages.success(request, "Вложение добавлено.")
                if is_ajax:
                    return JsonResponse({"success": True})
                return redirect("tickets:ticket_detail", pk=ticket.pk)

    # Query IT users for assignment dropdown
    it_users = []
    if request.user.is_authenticated and request.user.is_it():
        it_users = User.objects.filter(
            role__in=[User.Roles.IT_STAFF, User.Roles.IT_ADMIN],
            is_active=True
        ).order_by('username')
        if not it_users:
            messages.warning(request, "Нет активных ИТ-сотрудников для назначения.")

    # Determine is_it and is_principal flags for template
    is_it = request.user.is_authenticated and request.user.is_it()
    is_principal = request.user.is_authenticated and request.user.is_principal()

    context = {
        "ticket": ticket,
        "comment_form": comment_form,
        "attachment_form": attachment_form,
        "public_comments": public_comments,
        "internal_comments": internal_comments,
        "is_it": is_it,
        "is_principal": is_principal,
        "is_guest": not request.user.is_authenticated,
    }
    # Only include it_users if the user is IT
    if is_it:
        context["it_users"] = it_users
    return render(request, "tickets/detail.html", context)


# ----------------------------------------------------------------------
@csrf_protect
def guest_ticket_create(request):
    if request.user.is_authenticated:
        return redirect("tickets:ticket_create")

    # Prevent duplicate creation via back button
    last_id = request.session.get('last_created_ticket_id')
    last_time = request.session.get('last_created_time', 0)
    now_ts = timezone.now().timestamp()
    if last_id and (now_ts - last_time < 30):
        del request.session['last_created_ticket_id']
        del request.session['last_created_time']
        return redirect("tickets:guest_ticket_detail", pk=last_id)

    if request.method == "POST":
        form = GuestTicketForm(request.POST, request=request)
        attachment_form = GuestAttachmentForm(request.POST, request.FILES)
        if form.is_valid() and attachment_form.is_valid():
            ticket = form.save(commit=False)
            ticket.save()

            files = attachment_form.cleaned_data.get("files", [])
            for f in files:
                safe_name = f"{uuid.uuid4()}{os.path.splitext(f.name)[1]}"
                f.name = safe_name
                TicketAttachment.objects.create(
                    ticket=ticket,
                    file=f,
                    uploaded_by=None,
                )

            if ticket.guest_email:
                try:
                    send_ticket_created_email.delay(ticket.guest_email, ticket.ticket_number)
                except Exception:
                    logger.warning("Could not queue email for guest ticket %s.", ticket.ticket_number)

            guest_tickets = request.session.get("guest_tickets", [])
            guest_tickets.append(str(ticket.pk))
            request.session["guest_tickets"] = guest_tickets
            request.session['last_created_ticket_id'] = str(ticket.pk)
            request.session['last_created_time'] = now_ts

            messages.success(request, f"Заявка {ticket.ticket_number} создана. Сохраните этот номер.")
            return redirect("tickets:guest_ticket_detail", pk=ticket.pk)
    else:
        form = GuestTicketForm(request=request)
        attachment_form = GuestAttachmentForm()

    return render(request, "tickets/guest_create.html", {
        "form": form,
        "attachment_form": attachment_form,
    })

@login_required
def ticket_delete(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    if not (request.user.role == User.Roles.TEACHER
            and ticket.created_by == request.user
            and ticket.assigned_to is None):
        messages.error(request, "У вас нет прав на удаление этой заявки.")
        return redirect("tickets:ticket_detail", pk=ticket.pk)

    # Notify IT staff before deletion
    from apps.notifications.utils import create_notification
    from apps.notifications.models import Notification
    it_users = User.objects.filter(
        role__in=[User.Roles.IT_STAFF, User.Roles.IT_ADMIN],
        is_active=True
    )
    for it_user in it_users:
        create_notification(
            recipient_id=it_user.pk,
            ticket=ticket,
            notif_type=Notification.Type.COMMENT,   # reuse comment type
            message=f"Заявка {ticket.ticket_number} была удалена учителем {request.user.username}.",
            triggered_by=request.user,
        )
    ticket.delete()
    messages.success(request, f"Заявка {ticket.ticket_number} удалена.")
    return redirect("home")

def guest_ticket_detail(request, pk):
    if request.user.is_authenticated:
        # Authenticated users should use the normal ticket_detail view
        return redirect("tickets:ticket_detail", pk=pk)

    guest_tickets = request.session.get("guest_tickets", [])
    if str(pk) not in guest_tickets:
        return redirect("home")

    ticket = get_object_or_404(
        Ticket.objects.select_related("created_by", "assigned_to").prefetch_related(
            "comments__author", "attachments__uploaded_by", "history__changed_by"
        ),
        pk=pk,
    )
    return render(request, "tickets/detail.html", {
        "ticket": ticket,
        "is_guest": True,
        "public_comments": [c for c in ticket.comments.all() if not c.internal],
        "internal_comments": [],
        "comment_form": None,
        "attachment_form": None,
        "is_it": False,
    })