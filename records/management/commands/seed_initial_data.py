from django.core.management.base import BaseCommand
from django.utils.text import slugify
from django.apps import apps
from records.models import MedicalSpecialty, DocumentType, MedicalCategory, Tag
from django.utils.translation import gettext_lazy as _l

class Command(BaseCommand):
    help = 'Seeds the database with initial specialties, document types, categories, and corresponding tags.'

    def handle(self, *args, **options):
        self.stdout.write('Seeding initial data...')
        self.seed_document_types()
        self.seed_specialties()
        self.seed_categories()
        self.stdout.write(self.style.SUCCESS('Successfully seeded initial data.'))

    def seed_document_types(self):
        doc_types_data = sorted([
            {"bg": "Амбулаторен лист", "en": "Outpatient Sheet"},
            {"bg": "Биопсия", "en": "Biopsy"},
            {"bg": "Болничен лист", "en": "Sick Leave Certificate"},
            {"bg": "Ваксинационен картон / сертификат", "en": "Vaccination Card / Certificate"},
            {"bg": "Гастроскопия / Колонскопия", "en": "Gastroscopy / Colonoscopy"},
            {"bg": "електрокардиограма", "en": "Electrocardiogram"},
            {"bg": "електромиография", "en": "Electromyography"},
            {"bg": "Епикриза (докторски отчет от болница)", "en": "Epicrisis (Hospital Discharge Summary)"},
            {"bg": "Кръвни изследвания", "en": "Blood Test Results"},
            {"bg": "Мамография", "en": "Mammography"},
            {"bg": "Медицинско заключение / становище", "en": "Medical Conclusion / Opinion"},
            {"bg": "Медицинско направление", "en": "Medical Referral"},
            {"bg": "Направление", "en": "Referral Slip"},
            {"bg": "Оперативен протокол", "en": "Surgical Protocol"},
            {"bg": "Разчитане на Ехография / Ултразвук", "en": "Ultrasound Report"},
            {"bg": "Разчитане на КТ Компютърна томография", "en": "CT Scan Report"},
            {"bg": "Разчитане на Рентгенова снимка", "en": "X-ray Report"},
            {"bg": "Разчитане на ЯМР Ядрено-магнитен резонанс", "en": "MRI Report"},
            {"bg": "Рецепта", "en": "Prescription"},
            {"bg": "Сертификат / документ за пътуване", "en": "Certificate / Travel Document"},
            {"bg": "ТЕЛК решение", "en": "Disability Committee Decision"},
            {"bg": "Хистологичен резултат / Патология", "en": "Histology Result / Pathology"},
        ], key=lambda x: x['bg'])

        self.stdout.write('Seeding document types and tags...')
        TranslationModel = apps.get_model('records', 'DocumentTypeTranslation')
        for data in doc_types_data:
            if not TranslationModel.objects.filter(language_code='bg', name=data['bg']).exists():
                slug = slugify(data['en'])
                obj = DocumentType(slug=slug, is_active=True)
                obj.set_current_language('bg'); obj.name = data['bg']
                obj.set_current_language('en'); obj.name = data['en']
                obj.save()
                Tag.objects.get_or_create(name=data['bg'], defaults={"category": "test_type"})
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(doc_types_data)} document types and tags.'))

    def seed_specialties(self):
        specialties_data = sorted([
            {"bg": "Акушерство и гинекология", "en": "Obstetrics and Gynecology"},
            {"bg": "Гастроентерология", "en": "Gastroenterology"},
            {"bg": "Дентална медицина", "en": "Dental Medicine"},
            {"bg": "Дерматология", "en": "Dermatology"},
            {"bg": "Ендокринология", "en": "Endocrinology"},
            {"bg": "Инфекциозни болести", "en": "Infectious Diseases"},
            {"bg": "Кардиология", "en": "Cardiology"},
            {"bg": "Неврология", "en": "Neurology"},
            {"bg": "Нефрология", "en": "Nephrology"},
            {"bg": "Обща медицина / Семейна медицина", "en": "General Practice / Family Medicine"},
            {"bg": "Ортопедия и травматология", "en": "Orthopedics and Traumatology"},
            {"bg": "Офталмология", "en": "Ophthalmology"},
            {"bg": "Педиатрия", "en": "Pediatrics"},
            {"bg": "Психиатрия", "en": "Psychiatry"},
            {"bg": "Пулмология", "en": "Pulmonology"},
            {"bg": "Ревматология", "en": "Rheumatology"},
            {"bg": "УНГ (Уши-Нос-Гърло)", "en": "ENT (Ear-Nose-Throat)"},
            {"bg": "Урология", "en": "Urology"},
            {"bg": "Хематология", "en": "Hematology"},
            {"bg": "Хирургия", "en": "Surgery"},
        ], key=lambda x: x['bg'])

        self.stdout.write('Seeding medical specialties and tags...')
        TranslationModel = apps.get_model('records', 'MedicalSpecialtyTranslation')
        for data in specialties_data:
            if not TranslationModel.objects.filter(language_code='bg', name=data['bg']).exists():
                obj = MedicalSpecialty(is_active=True)  # БЕЗ slug – моделът няма такова поле
                obj.set_current_language('bg'); obj.name = data['bg']
                obj.set_current_language('en'); obj.name = data['en']
                obj.save()
                Tag.objects.get_or_create(name=data['bg'], defaults={"category": "specialty"})
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(specialties_data)} medical specialties and tags."))


    def seed_categories(self):
        categories_data = sorted([
            {"bg": "Ваксинация / Имунизация", "en": "Vaccination / Immunization"},
            {"bg": "Дентално лечение", "en": "Dental Treatment"},
            {"bg": "Интервенция", "en": "Intervention"},
            {"bg": "Консултация", "en": "Consultation"},
            {"bg": "Миниинвазивна процедура", "en": "Minimally Invasive Procedure"},
            {"bg": "Преглед", "en": "Examination"},
            {"bg": "Профилактичен преглед", "en": "Preventive Check-up"},
            {"bg": "Психотерапевтична сесия", "en": "Psychotherapy Session"},
            {"bg": "Скрининг", "en": "Screening"},
            {"bg": "Физиотерапия / Рехабилитация", "en": "Physiotherapy / Rehabilitation"},
            {"bg": "Хирургична операция", "en": "Surgical Operation"},
            {"bg": "Хоспитализация", "en": "Hospitalization"},
        ], key=lambda x: x['bg'])

        self.stdout.write('Seeding medical categories and tags...')
        TranslationModel = apps.get_model('records', 'MedicalCategoryTranslation')
        for data in categories_data:
            if not TranslationModel.objects.filter(language_code='bg', name=data['bg']).exists():
                slug = slugify(data['en'])
                obj = MedicalCategory(slug=slug, is_active=True)
                obj.set_current_language('bg'); obj.name = data['bg']
                obj.set_current_language('en'); obj.name = data['en']
                obj.save()
                Tag.objects.get_or_create(name=data['bg'], defaults={"category": "time"})
        self.stdout.write(self.style.SUCCESS(f'Seeded {len(categories_data)} medical categories and tags.'))
