from django.contrib import admin

from .models import Ticket, TicketAttachment, TicketComment, TicketHistory


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "status",
        "urgency",
        "room_number",
        "created_by",
        "assigned_to",
        "is_overdue",
        "created_at",
        "updated_at",
    )
    search_fields = (
        "ticket_number",
        "room_number",
        "device_asset_tag",
        "description",
        "created_by__username",
        "assigned_to__username",
    )
    list_filter = ("status", "urgency", "category", "device_type", "is_overdue")
    autocomplete_fields = ("created_by", "assigned_to")
    readonly_fields = ("ticket_number", "created_at", "updated_at", "resolved_at", "closed_at")
    ordering = ("-created_at",)


@admin.register(TicketAttachment)
class TicketAttachmentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "uploaded_by", "uploaded_at")
    search_fields = ("ticket__ticket_number", "uploaded_by__username")
    autocomplete_fields = ("ticket", "uploaded_by")
    readonly_fields = ("uploaded_at",)


@admin.register(TicketComment)
class TicketCommentAdmin(admin.ModelAdmin):
    list_display = ("ticket", "author", "internal", "created_at")
    search_fields = ("ticket__ticket_number", "author__username", "comment")
    list_filter = ("internal", "created_at")
    autocomplete_fields = ("ticket", "author")
    readonly_fields = ("created_at",)


@admin.register(TicketHistory)
class TicketHistoryAdmin(admin.ModelAdmin):
    list_display = ("ticket", "old_status", "new_status", "changed_by", "changed_at")
    search_fields = ("ticket__ticket_number", "note", "changed_by__username")
    list_filter = ("changed_at",)
    autocomplete_fields = ("ticket", "changed_by")
    readonly_fields = ("changed_at",)