import random
from django import forms
from django.core.exceptions import ValidationError
from .models import Ticket

MAX_TOTAL_SIZE_MB = 50


import os
from django.core.exceptions import ValidationError

ALLOWED_EXTENSIONS = {
    'jpg', 'jpeg', 'png', 'gif', 'webp', 'svg',  # images
    'mp4', 'webm', 'mov', 'avi',                  # video
    'pdf', 'doc', 'docx', 'xls', 'xlsx',          # office
    'ppt', 'pptx', 'txt', 'csv'                   # common safe types
}

class MultipleFileField(forms.Field):
    def clean(self, value):
        """
        `value` is a list of UploadedFile objects (or None/empty list).
        """
        if value is None:
            return []

        # Ensure we always work with a list
        files = value if isinstance(value, list) else [value]
        total_size = 0
        for f in files:
            ext = os.path.splitext(f.name)[1].lower().lstrip('.')
            if ext not in ALLOWED_EXTENSIONS:
                raise ValidationError(f"Недопустимый тип файла: .{ext}")
            total_size += f.size
        if total_size > MAX_TOTAL_SIZE_MB * 1024 * 1024:
            raise ValidationError(f"Общий размер файлов превышает {MAX_TOTAL_SIZE_MB} МБ.")
        return files

class MathCaptchaWidget(forms.Widget):
    """Renders a math question and a text input for the answer."""
    def render(self, name, value, attrs=None, renderer=None):
        # Retrieve variables from widget attrs set in the form field
        a = self.attrs.get('a', 0)
        b = self.attrs.get('b', 0)
        op = self.attrs.get('op', '+')
        question = f"{a} {op} {b} = ?"
        html = f'<span>{question}</span> '
        html += f'<input type="text" name="{name}" required '
        if attrs:
            html += ' ' + ' '.join(f'{k}="{v}"' for k,v in attrs.items())
        html += '>'
        return html

class MathCaptchaField(forms.IntegerField):
    """Custom captcha field: solve a simple arithmetic operation."""
    widget = MathCaptchaWidget

    def __init__(self, *args, **kwargs):
        kwargs['min_value'] = 0
        kwargs['max_value'] = 9999
        super().__init__(*args, **kwargs)

    def clean(self, value):
        # Get the stored answer from session (session must be available)
        request = self.form.request if hasattr(self, 'form') else None
        if not request:
            raise forms.ValidationError("Session error.")
        stored_answer = request.session.pop('captcha_answer', None)
        if stored_answer is None:
            raise forms.ValidationError("Captcha expired, please try again.")
        if int(value) != stored_answer:
            raise forms.ValidationError("Wrong answer.")
        return value


class GuestTicketForm(forms.ModelForm):
    guest_name = forms.CharField(label="Ваше имя", max_length=150)
    guest_email = forms.EmailField(label="Email (для уведомлений)", required=False)
    captcha = forms.IntegerField(label="Сколько будет?", required=True)

    class Meta:
        model = Ticket
        fields = [
            "room_number",
            "device_type",
            # "device_asset_tag", уже не нужно просто.
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

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.fields['urgency'].choices = [('low', 'Низкая')]
        self.fields['urgency'].initial = 'low'
        self.fields['urgency'].widget.attrs['disabled'] = True

        # Always generate (or retrieve) the captcha question.
        if self.request:
            if not self.is_bound:
                a = random.randint(1, 20)
                b = random.randint(1, 20)
                self.captcha_question = f"{a} + {b} = ?"
                self.request.session['captcha_answer'] = a + b
                self.request.session['captcha_question'] = self.captcha_question
            else:
                # Bound form: use the saved question from the previous request's session
                self.captcha_question = self.request.session.get('captcha_question', '?')
        else:
            self.captcha_question = '?'  # fallback

    def clean_captcha(self):
        if self.request is None:
            raise forms.ValidationError("Ошибка сессии: запрос не передан.")
        value = self.cleaned_data.get('captcha')
        stored_answer = self.request.session.pop('captcha_answer', None)
        if stored_answer is None:
            raise forms.ValidationError("Время капчи истекло, попробуйте ещё раз.")
        if int(value) != stored_answer:
            raise forms.ValidationError("Неверный ответ.")
        return value

    def clean(self):
        cleaned_data = super().clean()
        self.guest_name = cleaned_data.get('guest_name')
        self.guest_email = cleaned_data.get('guest_email')
        return cleaned_data

    def save(self, commit=True):
        ticket = super().save(commit=False)
        ticket.created_by = None
        ticket.guest_name = self.guest_name
        ticket.guest_email = self.guest_email
        if commit:
            ticket.save()
        return ticket

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class GuestAttachmentForm(forms.Form):
    files = MultipleFileField(
        required=False,
        widget=MultipleFileInput(attrs={"accept": "image/*,video/*,.pdf,.doc,.docx,.xls,.xlsx"}),
        help_text="Можно прикрепить несколько файлов (суммарно не более 50 МБ)."
    )