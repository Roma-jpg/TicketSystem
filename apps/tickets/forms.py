from django import forms
from .models import Ticket, TicketAttachment, TicketComment

from .guest_forms import MAX_TOTAL_SIZE_MB, MultipleFileField, MultipleFileInput

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = [
            "room_number",
            "device_type",
            # "device_asset_tag",
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
            # "device_asset_tag": "Инвентарный номер",
            "category": "Категория",
            "urgency": "Срочность",
            "description": "Описание проблемы",
        }


class TicketCommentForm(forms.ModelForm):
    class Meta:
        model = TicketComment
        fields = ["comment", "internal"]
        widgets = {
            "comment": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "comment": "Комментарий",
            "internal": "Внутренний (виден только ИТ‑сотрудникам)",
        }


import os
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',
    'mp4', 'webm', 'mov', 'avi',
    'pdf', 'doc', 'docx', 'xls', 'xlsx',
    'ppt', 'pptx', 'txt', 'csv',
}
MAX_UPLOAD_SIZE_MB = 50

class TicketAttachmentForm(forms.ModelForm):
    class Meta:
        model = TicketAttachment
        fields = ["file"]

    def clean_file(self):
        file = self.cleaned_data.get("file")
        if file:
            ext = os.path.splitext(file.name)[1].lower().lstrip('.')
            if ext not in ALLOWED_EXTENSIONS:
                raise ValidationError(f"Недопустимый тип файла: .{ext}")
            if file.size > MAX_UPLOAD_SIZE_MB * 1024 * 1024:
                raise ValidationError(f"Файл слишком большой (макс. {MAX_UPLOAD_SIZE_MB} МБ).")
        return file

class UserAttachmentForm(forms.Form):
    files = MultipleFileField(
        required=False,
        widget=MultipleFileInput(
            attrs={
                "accept": "image/*,video/*,.pdf,.doc,.docx,.xls,.xlsx"
            }
        ),
        help_text="Можно прикрепить несколько файлов (суммарно не более 50 МБ).",
    )