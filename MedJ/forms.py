# MedJ/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm  # , UserChangeForm # UserChangeForm is not used here
from django.contrib.auth import get_user_model
from .models import Document, MedicalEvent, MedicalCategory, MedicalSpecialty, DocumentTag  # Import necessary models


# Form for custom user creation (already exists)
class CustomUserCreationForm(UserCreationForm):
    email = forms.EmailField(label='Имейл', max_length=254, help_text='Въведете валиден имейл адрес.')

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = UserCreationForm.Meta.fields + ('email',)


# NEW: Form for Document Upload
class DocumentUploadForm(forms.ModelForm):
    class Meta:
        model = Document
        fields = ['file']  # Only file is uploaded via this form initially
        widgets = {
            'file': forms.ClearableFileInput(attrs={
                'class': 'block w-full text-sm text-gray-900 border border-gray-300 rounded-lg cursor-pointer bg-gray-50 focus:outline-none'}),
        }
        labels = {
            'file': 'Изберете файл',
        }


# NEW: Form for Medical Event details (for editing/display)
class MedicalEventForm(forms.ModelForm):
    # These fields might be used in a form for manual creation/editing of events
    # Or to bind initial data to the event_detail_page
    event_date = forms.DateField(
        label='Дата на събитието',
        widget=forms.DateInput(attrs={'type': 'date',
                                      'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}),
        required=False
    )
    summary = forms.CharField(
        label='Обобщение',
        widget=forms.Textarea(attrs={'rows': 4,
                                     'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}),
        required=False
    )
    diagnosis = forms.CharField(
        label='Диагноза',
        widget=forms.Textarea(attrs={'rows': 2,
                                     'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}),
        required=False
    )
    treatment_plan = forms.CharField(
        label='План за лечение',
        widget=forms.Textarea(attrs={'rows': 2,
                                     'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}),
        required=False
    )

    # These could be dropdowns populated dynamically or with fixed choices
    # If using dropdowns, ensure appropriate querysets are passed in view context for choices
    event_type_title = forms.ChoiceField(
        label='Тип събитие',
        choices=MedicalEvent.EventType.choices,
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}),
        required=False
    )
    category = forms.ModelChoiceField(
        queryset=MedicalCategory.objects.all(),
        label='Категория',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}),
        required=False
    )
    specialty = forms.ModelChoiceField(
        queryset=MedicalSpecialty.objects.all(),
        label='Специалност',
        widget=forms.Select(attrs={
            'class': 'mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-300 focus:ring focus:ring-indigo-200 focus:ring-opacity-50'}),
        required=False
    )

    # Practitioners and Tags are ManyToMany, typically handled outside simple ModelForms
    # For now, keeping only basic fields in ModelForm. If complex M2M widgets needed,
    # they might be added here or handled separately in views/JS.

    class Meta:
        model = MedicalEvent
        fields = [
            'event_type_title', 'event_date', 'summary', 'diagnosis',
            'treatment_plan', 'category', 'specialty'
        ]
        # Exclude patient and source_document as they are set by the view logic
        # exclude = ['patient', 'source_document', 'created_at', 'updated_at', 'tags', 'practitioners']