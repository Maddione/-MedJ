from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import (
    Document,
    LabTestMeasurement,
    PatientProfile,
    MedicalEvent,
    Tag,
    DocumentShare,
)

User = get_user_model()


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label=_("Имейл"))
    phone = forms.CharField(label=_("Телефон"), required=False)

    class Meta:
        model = User
        fields = ["username", "email", "phone", "password1", "password2"]


class LoginForm(AuthenticationForm):
    username = forms.CharField(label=_("Потребителско име или имейл"))
    password = forms.CharField(label=_("Парола"), widget=forms.PasswordInput)


class PatientProfileForm(forms.ModelForm):
    class Meta:
        model = PatientProfile
        fields = [
            "first_name_bg",
            "middle_name_bg",
            "last_name_bg",
            "first_name_en",
            "middle_name_en",
            "last_name_en",
            "date_of_birth",
            "gender",
            "phone_number",
            "address",
            "blood_type",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "first_name_bg": _("Собствено име (БГ)"),
            "middle_name_bg": _("Бащино име (БГ)"),
            "last_name_bg": _("Фамилия (БГ)"),
            "first_name_en": _("First name (EN)"),
            "middle_name_en": _("Middle name (EN)"),
            "last_name_en": _("Last name (EN)"),
            "date_of_birth": _("Дата на раждане"),
            "gender": _("Пол"),
            "phone_number": _("Телефон"),
            "address": _("Адрес"),
            "blood_type": _("Кръвна група"),
        }


class MedicalEventForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "min-w-64"})
    )

    class Meta:
        model = MedicalEvent
        fields = ["specialty", "event_date", "summary", "tags"]
        widgets = {
            "event_date": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.TextInput(),
        }
        labels = {
            "specialty": _("Специалност"),
            "event_date": _("Дата на събитие"),
            "summary": _("Кратко описание"),
            "tags": _("Етикети"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tags"].queryset = Tag.objects.filter(is_active=True).order_by("translations__name")


class DocumentUploadForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "min-w-64"})
    )

    class Meta:
        model = Document
        fields = [
            "file",
            "specialty",
            "category",
            "doc_type",
            "document_date",
            "summary",
            "notes",
            "tags",
        ]
        widgets = {
            "document_date": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.TextInput(),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "file": _("Файл"),
            "specialty": _("Специалност"),
            "category": _("Категория"),
            "doc_type": _("Вид документ"),
            "document_date": _("Дата на документа"),
            "summary": _("Кратко описание"),
            "notes": _("Бележки"),
            "tags": _("Етикети"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tags"].queryset = Tag.objects.filter(is_active=True).order_by("translations__name")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("specialty"):
            self.add_error("specialty", _("Задължително поле"))
        if not cleaned.get("category"):
            self.add_error("category", _("Задължително поле"))
        if not cleaned.get("doc_type"):
            self.add_error("doc_type", _("Задължително поле"))
        if not cleaned.get("file"):
            self.add_error("file", _("Моля, прикачете файл"))
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        f = self.cleaned_data.get("file")
        if f and not instance.doc_kind:
            name = f.name.lower()
            if name.endswith((".png", ".jpg", ".jpeg")):
                instance.doc_kind = "image"
            elif name.endswith(".pdf"):
                instance.doc_kind = "pdf"
            else:
                instance.doc_kind = "other"
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class DocumentEditForm(forms.ModelForm):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "min-w-64"})
    )

    class Meta:
        model = Document
        fields = [
            "specialty",
            "category",
            "doc_type",
            "document_date",
            "summary",
            "notes",
            "tags",
        ]
        widgets = {
            "document_date": forms.DateInput(attrs={"type": "date"}),
            "summary": forms.TextInput(),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }
        labels = {
            "specialty": _("Специалност"),
            "category": _("Категория"),
            "doc_type": _("Вид документ"),
            "document_date": _("Дата на документа"),
            "summary": _("Кратко описание"),
            "notes": _("Бележки"),
            "tags": _("Етикети"),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["tags"].queryset = Tag.objects.filter(is_active=True).order_by("translations__name")

    def clean(self):
        cleaned = super().clean()
        if not cleaned.get("specialty"):
            self.add_error("specialty", _("Задължително поле"))
        if not cleaned.get("category"):
            self.add_error("category", _("Задължително поле"))
        if not cleaned.get("doc_type"):
            self.add_error("doc_type", _("Задължително поле"))
        return cleaned


class LabTestMeasurementForm(forms.ModelForm):
    class Meta:
        model = LabTestMeasurement
        fields = ["indicator", "value", "measured_at"]
        widgets = {
            "measured_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
        labels = {
            "indicator": _("Показател"),
            "value": _("Стойност"),
            "measured_at": _("Дата и час"),
        }

    def clean_measured_at(self):
        v = self.cleaned_data.get("measured_at")
        return v or timezone.now()


class DocumentShareForm(forms.ModelForm):
    class Meta:
        model = DocumentShare
        fields = ["expires_at", "is_active"]
        widgets = {
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }
        labels = {
            "expires_at": _("Валиден до"),
            "is_active": _("Активен"),
        }


class SearchFilterForm(forms.Form):
    q = forms.CharField(label=_("Търси"), required=False)
    specialty = forms.ModelChoiceField(label=_("Специалност"), queryset=Tag.objects.none(), required=False)
    category = forms.ModelChoiceField(label=_("Категория"), queryset=Tag.objects.none(), required=False)
    doc_type = forms.ModelChoiceField(label=_("Вид документ"), queryset=Tag.objects.none(), required=False)
    date_from = forms.DateField(label=_("От дата"), required=False, widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(label=_("До дата"), required=False, widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["specialty"].queryset = Tag.objects.filter(kind="specialty", is_active=True).order_by("translations__name")
        self.fields["category"].queryset = Tag.objects.filter(kind="category", is_active=True).order_by("translations__name")
        self.fields["doc_type"].queryset = Tag.objects.filter(kind="doc_type", is_active=True).order_by("translations__name")
