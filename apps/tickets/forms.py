from django import forms
from .models import Ticket, TicketAttachment, TicketComment


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
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
        }
        labels = {
            "room_number": "Номер кабинета",
            "device_type": "Тип устройства",
            "device_asset_tag": "Инвентарный номер",
            "category": "Категория",
            "urgency": "Срочность",
            "description": "Описание проблемы",
        }


class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["comment"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4}),
        }


class TicketAttachmentForm(forms.ModelForm):
    class Meta:
        model = TicketAttachment
        fields = ["file"]