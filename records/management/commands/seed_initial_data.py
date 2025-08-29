from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.apps import apps
from records.models import MedicalSpecialty, DocumentType


class Command(BaseCommand):
    help = 'Seeds the database with initial specialties and document types.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding initial data...')
        self.seed_specialties()
        self.seed_document_types()
        self.stdout.write(self.style.SUCCESS('Successfully seeded initial data.'))

    def seed_specialties(self):
        specialties_data = [
            {"bg": "Кардиология", "en": "Cardiology"},
            {"bg": "Ендокринология", "en": "Endocrinology"},
            {"bg": "Вътрешни болести", "en": "Internal Medicine"},
            {"bg": "Неврология", "en": "Neurology"},
            {"bg": "Гастроентерология", "en": "Gastroenterology"},
            {"bg": "Ортопедия и травматология", "en": "Orthopedics and Traumatology"},
            {"bg": "Акушерство и гинекология (АГ)", "en": "Obstetrics and Gynecology (OB/GYN)"},
            {"bg": "Хирургия", "en": "Surgery"},
            {"bg": "Пулмология (Белодробни болести)", "en": "Pulmonology (Lung Diseases)"},
            {"bg": "Обща (Семейна) медицина", "en": "General (Family) Medicine"},
            {"bg": "Педиатрия (Детски болести)", "en": "Pediatrics (Children's Diseases)"},
            {"bg": "Дерматология (Кожни болести)", "en": "Dermatology (Skin Diseases)"},
            {"bg": "Уши, нос и гърло (УНГ)", "en": "Ear, Nose, and Throat (ENT)"},
            {"bg": "Урология", "en": "Urology"},
            {"bg": "Очни болести (Офталмология)", "en": "Ophthalmology (Eye Diseases)"},
            {"bg": "Нефрология", "en": "Nephrology"},
        ]

        self.stdout.write('Seeding medical specialties...')
        TranslationModel = apps.get_model('records', 'MedicalSpecialtyTranslation')
        for data in specialties_data:
            if not TranslationModel.objects.filter(language_code='bg', name=data['bg']).exists():
                obj = MedicalSpecialty()
                obj.set_current_language('bg')
                obj.name = data['bg']
                obj.set_current_language('en')
                obj.name = data['en']
                obj.save()
                self.stdout.write(f'  Created specialty: {data["bg"]}')

    def seed_document_types(self):
        doc_types_data = [
            {"bg": "Кръвни изследвания", "en": "Blood Tests"},
            {"bg": "Изследване на урина", "en": "Urine Test"},
            {"bg": "Епикриза", "en": "Discharge Summary"},
            {"bg": "Амбулаторен лист", "en": "Outpatient Sheet"},
            {"bg": "Консултация", "en": "Consultation"},
            {"bg": "Рецепта", "en": "Prescription"},
            {"bg": "Електрокардиограма (ЕКГ)", "en": "Electrocardiogram (ECG)"},
            {"bg": "Запис на детски сърдечни тонове", "en": "Fetal Heart Tone Record"},
            {"bg": "Образна диагностика", "en": "Imaging"},
            {"bg": "Патологично изследване", "en": "Pathological Study"},
            {"bg": "Ваксинационен картон / Имунизации", "en": "Vaccination Card / Immunizations"},
            {"bg": "Оперативен протокол", "en": "Surgical Protocol"},
            {"bg": "Медицинско направление (Талон)", "en": "Referral"},
            {"bg": "Болничен лист", "en": "Sick Leave Certificate"},
            {"bg": "Протокол от комисия / ТЕЛК", "en": "Committee Protocol"},
            {"bg": "Информирано съгласие", "en": "Informed Consent"},
            {"bg": "Справка / Медицинска бележка", "en": "Report / Medical Note"},
        ]

        self.stdout.write('Seeding document types...')
        TranslationModel = apps.get_model('records', 'DocumentTypeTranslation')
        for data in doc_types_data:
            if not TranslationModel.objects.filter(language_code='bg', name=data['bg']).exists():
                slug = slugify(data['en'])
                obj = DocumentType(slug=slug, is_active=True)
                obj.set_current_language('bg')
                obj.name = data['bg']
                obj.set_current_language('en')
                obj.name = data['en']
                obj.save()
                self.stdout.write(f'  Created document type: {data["bg"]}')