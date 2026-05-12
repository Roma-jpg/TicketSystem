from django.contrib import admin

from .models import (
	Ticket,
	TicketAttachment,
	TicketComment,
	TicketHistory,
)


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):

	list_display = (
		"ticket_number",
		"status",
		"urgency",
		"room_number",
		"assigned_to",
		"created_at",
	)

	search_fields = (
		"ticket_number",
		"room_number",
		"device_asset_tag",
	)

	list_filter = (
		"status",
		"urgency",
		"category",
	)