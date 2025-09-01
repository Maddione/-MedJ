from django import forms
from django.utils.translation import gettext_lazy as _l
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (
    Document,
    MedicalSpecialty,
    DocumentType,
    MedicalEvent,
    Tag,
    LabIndicator,
    LabTestMeasurement,
)

from .models import (
    Document, MedicalSpecialty, DocumentType, MedicalEvent,
    MedicalCategory,
    Tag, LabIndicator, LabTestMeasurement,
)
UserModel = get_user_model()

class LoginForm(AuthenticationForm):
    pass

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_l("Имейл"))
    class Meta:
        model = UserModel
        fields = ("username", "email", "first_name", "last_name")
    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and UserModel.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(_l("Потребител с този имейл адрес вече съществува."))
        return email

class DocumentTagForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ["tags"]
        widgets = {"tags": forms.SelectMultiple(attrs={"class": "form-multiselect"})}

class EventTagForm(forms.ModelForm):
    class Meta:
        model = MedicalEvent
        fields = ["tags"]
        widgets = {"tags": forms.SelectMultiple(attrs={"class": "form-multiselect"})}

class TagCreationForm(forms.ModelForm):
    class Meta:
        model = Tag
        fields = ["name", "category"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": _l("Въведете име на таг")}),
        }

class DocumentUploadForm(forms.Form):
    doc_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.filter(is_active=True),
        label=_l("Вид документ"),
        empty_label=_l("Изберете вид документ"),
        required=True,
    )
    specialty = forms.ModelChoiceField(
        queryset=MedicalSpecialty.objects.filter(is_active=True),
        label=_l("Специалност"),
        empty_label=_l("Изберете специалност"),
        required=True,
    )
    category = forms.ModelChoiceField(
        queryset=MedicalCategory.objects.filter(is_active=True),
        label=_l("Категория"),
        empty_label=_l("Изберете категория"),
        required=True,
    )

    target_event = forms.ModelChoiceField(
        queryset=MedicalEvent.objects.none(),
        label=_l("Свържи със съществуващо събитие"),
        required=False,
    )
    new_event_date = forms.DateField(
        label=_l("Или създай ново събитие с дата"),
        required=False,
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    tags = forms.CharField(
        label=_l("Тагове (разделени със запетая)"),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": _l("напр. кръвна картина, профилактичен")}),
    )

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        initial_specialty = kwargs.pop("initial_specialty", None)
        initial_category = kwargs.pop("initial_category", None)
        super().__init__(*args, **kwargs)

        if initial_specialty:
            self.fields["specialty"].initial = getattr(initial_specialty, "pk", initial_specialty)
        if initial_category:
            self.fields["category"].initial = getattr(initial_category, "pk", initial_category)

        if user and hasattr(user, "patientprofile"):
            try:
                spec_id = int((self.data or {}).get("specialty"))
            except (TypeError, ValueError):
                spec_id = None
            try:
                cat_id = int((self.data or {}).get("category"))
            except (TypeError, ValueError):
                cat_id = None

            qs = MedicalEvent.objects.filter(patient=user.patientprofile)
            if spec_id:
                qs = qs.filter(specialty_id=spec_id)
            if cat_id:
                qs = qs.filter(category_id=cat_id)
            self.fields["target_event"].queryset = qs.order_by("-event_date")

    def clean(self):
        cleaned = super().clean()
        target = cleaned.get("target_event")
        new_date = cleaned.get("new_event_date")
        if not target and not new_date:
            raise forms.ValidationError(_l("Изберете събитие или въведете дата за ново събитие."))
        if target and new_date:
            raise forms.ValidationError(_l("Изберете само едно: съществуващо събитие или нова дата."))
        return cleaned

    def get_normalized_tags(self):
        raw = self.cleaned_data.get("tags") or ""
        parts = [p.strip() for p in raw.split(",") if p.strip()]
        unique = []
        for p in parts:
            if p not in unique:
                unique.append(p)
        return unique

class DocumentEditForm(forms.ModelForm):
    doc_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.filter(is_active=True),
        label=_l("Вид документ"),
        required=True,
    )
    document_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_l("Дата на документа"),
        required=False,
    )
    class Meta:
        model = Document
        fields = ["doc_type", "document_date", "summary", "notes"]

class ShareCreateForm(forms.Form):
    duration_hours = forms.IntegerField(min_value=1, label=_l("Валидност (часове)"))

class LabIndicatorForm(forms.ModelForm):
    class Meta:
        model = LabIndicator
        fields = ["name", "unit", "reference_low", "reference_high"]

class LabTestMeasurementForm(forms.ModelForm):
    class Meta:
        model = LabTestMeasurement
        fields = ["medical_event", "indicator", "value", "measured_at"]
