from django import forms
from django.utils.translation import gettext_lazy as _l
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import (
    Document,
    MedicalSpecialty,
    DocumentType,
    PractitionerProfile,
    MedicalEvent,
    Tag,
)

UserModel = get_user_model()

class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].widget.attrs.update(
            {'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline'}
        )
        self.fields['password'].widget.attrs.update(
            {'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 mb-3 leading-tight focus:outline-none focus:shadow-outline'}
        )

class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True, label=_l("Имейл"))

    class Meta:
        model = UserModel
        fields = ["username", "email", "first_name", "last_name"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field_name, field in self.fields.items():
            field.widget.attrs.update({'class': 'shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline mb-2'})

class DocumentUploadForm(forms.ModelForm):
    specialty = forms.ModelChoiceField(queryset=MedicalSpecialty.objects.all(), label=_l("Специалност"))
    doc_type = forms.ModelChoiceField(queryset=DocumentType.objects.filter(is_active=True), label=_l("Вид документ"))
    practitioner = forms.ModelChoiceField(queryset=PractitionerProfile.objects.all(), required=False, label=_l("Лекар"))
    document_date = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), label=_l("Дата на документа"))
    attach_to_event = forms.ModelChoiceField(queryset=MedicalEvent.objects.none(), required=False, label=_l("Прикачи към събитие"))
    file = forms.FileField(label=_l("Файл"))

    class Meta:
        model = Document
        fields = ["file", "doc_type", "document_date", "practitioner"]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["attach_to_event"].queryset = MedicalEvent.objects.none()
        if "specialty" in self.data and user and hasattr(user, "patient_profile"):
            try:
                spec_id = int(self.data.get("specialty"))
                self.fields["attach_to_event"].queryset = MedicalEvent.objects.filter(
                    patient=user.patient_profile, specialty_id=spec_id
                ).order_by("-event_date")
            except (TypeError, ValueError):
                self.fields["attach_to_event"].queryset = MedicalEvent.objects.none()

    def clean(self):
        cleaned = super().clean()
        return cleaned

class EventTagForm(forms.Form):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "w-full"}),
        label=_l("Тагове")
    )

class DocumentTagForm(forms.Form):
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.SelectMultiple(attrs={"class": "w-full"}),
        label=_l("Тагове")
    )

class MoveDocumentForm(forms.Form):
    target_event = forms.ModelChoiceField(queryset=MedicalEvent.objects.none(), required=False, label=_l("Премести в събитие"))
    new_event_date = forms.DateField(required=False, widget=forms.DateInput(attrs={"type": "date"}), label=_l("Или създай ново събитие на дата"))
    specialty = forms.ModelChoiceField(queryset=MedicalSpecialty.objects.all(), label=_l("Специалност"))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        initial_specialty = kwargs.pop("specialty", None)
        super().__init__(*args, **kwargs)
        if initial_specialty:
            self.fields["specialty"].initial = initial_specialty.pk if hasattr(initial_specialty, "pk") else initial_specialty
        if "specialty" in self.data and user and hasattr(user, "patient_profile"):
            try:
                spec_id = int(self.data.get("specialty"))
                self.fields["target_event"].queryset = MedicalEvent.objects.filter(
                    patient=user.patient_profile, specialty_id=spec_id
                ).order_by("-event_date")
            except (TypeError, ValueError):
                self.fields["target_event"].queryset = MedicalEvent.objects.none()

    def clean(self):
        cleaned = super().clean()
        target = cleaned.get("target_event")
        new_date = cleaned.get("new_event_date")
        if not target and not new_date:
            raise forms.ValidationError(_l("Изберете събитие или въведете дата за ново събитие."))
        if target and new_date:
            raise forms.ValidationError(_l("Изберете само едно: съществуващо събитие или нова дата."))
        return cleaned

class DocumentEditForm(forms.ModelForm):
    practitioner = forms.ModelChoiceField(
        queryset=PractitionerProfile.objects.all(),
        required=False,
        label=_l("Лекар"),
    )
    doc_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.filter(is_active=True),
        label=_l("Вид документ"),
    )
    document_date = forms.DateField(
        widget=forms.DateInput(attrs={"type": "date"}),
        label=_l("Дата на документа"),
    )

    class Meta:
        model = Document
        fields = ["doc_type", "document_date", "practitioner"]