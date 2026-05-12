from django import forms

from .models import Ticket, TicketComment


class TicketForm(forms.ModelForm):

	class Meta:
		model = Ticket

		fields = [
			"room_number",
			"device_type",
			"device_asset_tag",
			"category",
			"urgency",
			"description",
		]


class TicketCommentForm(forms.ModelForm):

	class Meta:
		model = TicketComment
		fields = ["comment"]