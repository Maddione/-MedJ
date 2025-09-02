from django.core.management.base import BaseCommand
from django.db import transaction
from parler.utils.context import switch_language
from records.models import DocumentType, MedicalCategory, MedicalSpecialty
from django.utils.text import slugify

def upsert_translated(model, slug, name_bg=None, name_en=None, is_active=True, description_bg=None, description_en=None, extra=None):
    obj, _ = model.objects.update_or_create(
        slug=slug,
        defaults={"is_active": is_active, **(extra or {})},
    )
    if name_bg:
        with switch_language(obj, "bg"):
            obj.name = name_bg
            if description_bg is not None:
                obj.description = description_bg
            obj.save()
    if name_en:
        with switch_language(obj, "en-us"):
            obj.name = name_en
            if description_en is not None:
                obj.description = description_en
            obj.save()
    return obj

DOC_TYPES = [
    {"slug": "blood-tests", "bg": "Кръвни изследвания", "en": "Blood tests"},
    {"slug": "outpatient-sheet", "bg": "Амбулаторен лист", "en": "Outpatient sheet"},
    {"slug": "discharge-summary", "bg": "Епикриза", "en": "Discharge summary"},
    {"slug": "prescription", "bg": "Рецепта", "en": "Prescription"},
    {"slug": "xray-report", "bg": "Разчитане на Рентгенова снимка", "en": "X-ray report"},
    {"slug": "ultrasound-report", "bg": "Разчитане на Ехография / Ултразвук", "en": "Ultrasound report"},
    {"slug": "mri-report", "bg": "Разчитане на ЯМР", "en": "MRI report"},
    {"slug": "ct-report", "bg": "Разчитане на КТ", "en": "CT report"},
    {"slug": "referral", "bg": "Направление", "en": "Referral"},
    {"slug": "histology", "bg": "Хистологичен резултат / Патология", "en": "Histology / Pathology"},
    {"slug": "administrative", "bg": "Административен документ", "en": "Administrative document"},
    {"slug": "telk", "bg": "ТЕЛК решение", "en": "TELK decision"},
    {"slug": "vaccination", "bg": "Ваксинационен картон / сертификат", "en": "Vaccination certificate"},
    {"slug": "ecg", "bg": "Електрокардиограма", "en": "ECG"},
    {"slug": "emg", "bg": "Електромиография", "en": "EMG"},
    {"slug": "mammography", "bg": "Мамография", "en": "Mammography"},
    {"slug": "endoscopy", "bg": "Гастро/Колоноскопия", "en": "Endoscopy"},
    {"slug": "op-protocol", "bg": "Оперативен протокол", "en": "Operative note"},
    {"slug": "medical-opinion", "bg": "Медицинско становище", "en": "Medical opinion"},
    {"slug": "travel-certificate", "bg": "Сертификат за пътуване", "en": "Travel certificate"},
]

CATEGORIES = [
    {"slug": "vaccination", "bg": "Ваксинация / Имунизация", "en": "Vaccination / Immunization"},
    {"slug": "physiotherapy", "bg": "Физиотерапия / Рехабилитация", "en": "Physiotherapy / Rehabilitation"},
    {"slug": "surgery", "bg": "Хирургична операция", "en": "Surgical operation"},
    {"slug": "minimally-invasive", "bg": "Миниинвазивна процедура", "en": "Minimally invasive procedure"},
    {"slug": "psychotherapy", "bg": "Психотерапевтична сесия", "en": "Psychotherapy session"},
    {"slug": "dental", "bg": "Дентално лечение", "en": "Dental treatment"},
    {"slug": "preventive", "bg": "Профилактичен преглед", "en": "Preventive check"},
    {"slug": "screening", "bg": "Скрининг", "en": "Screening"},
    {"slug": "consultation", "bg": "Консултация", "en": "Consultation"},
    {"slug": "intervention", "bg": "Интервенция", "en": "Intervention"},
    {"slug": "hospitalization", "bg": "Хоспитализация", "en": "Hospitalization"},
]

SPECIALTIES = [
    {"slug": "endocrinology", "bg": "Ендокринология", "en": "Endocrinology"},
    {"slug": "cardiology", "bg": "Кардиология", "en": "Cardiology"},
    {"slug": "neurology", "bg": "Неврология", "en": "Neurology"},
    {"slug": "hematology", "bg": "Хематология", "en": "Hematology"},
    {"slug": "gastroenterology", "bg": "Гастроентерология", "en": "Gastroenterology"},
    {"slug": "pediatrics", "bg": "Педиатрия", "en": "Pediatrics"},
    {"slug": "pulmonology", "bg": "Пулмология", "en": "Pulmonology"},
    {"slug": "nephrology", "bg": "Нефрология", "en": "Nephrology"},
    {"slug": "dermatology", "bg": "Дерматология", "en": "Dermatology"},
    {"slug": "obgyn", "bg": "Акушерство и гинекология", "en": "Obstetrics and Gynecology"},
    {"slug": "urology", "bg": "Урология", "en": "Urology"},
    {"slug": "surgery", "bg": "Хирургия", "en": "Surgery"},
    {"slug": "orthopedics", "bg": "Ортопедия и травматология", "en": "Orthopedics and Traumatology"},
    {"slug": "ent", "bg": "УНГ", "en": "ENT"},
    {"slug": "ophthalmology", "bg": "Офталмология", "en": "Ophthalmology"},
    {"slug": "psychiatry", "bg": "Психиатрия", "en": "Psychiatry"},
    {"slug": "rheumatology", "bg": "Ревматология", "en": "Rheumatology"},
    {"slug": "infectious", "bg": "Инфекциозни болести", "en": "Infectious diseases"},
    {"slug": "family-medicine", "bg": "Обща/Семейна медицина", "en": "Family medicine"},
    {"slug": "dental-medicine", "bg": "Дентална медицина", "en": "Dental medicine"},
]

class Command(BaseCommand):
    help = "Seed initial taxonomy data (idempotent)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Seeding initial data...")
        self.seed_document_types()
        self.seed_categories()
        self.seed_specialties()
        self.stdout.write(self.style.SUCCESS("Seeding complete."))

    def seed_document_types(self):
        self.stdout.write("Seeding document types and tags...")
        for row in DOC_TYPES:
            upsert_translated(
                DocumentType,
                slug=row["slug"],
                name_bg=row["bg"],
                name_en=row.get("en"),
                is_active=True,
            )

    def seed_categories(self):
        self.stdout.write("Seeding medical categories and tags...")
        for row in CATEGORIES:
            upsert_translated(
                MedicalCategory,
                slug=row["slug"],
                name_bg=row["bg"],
                name_en=row.get("en"),
                is_active=True,
            )

    def seed_specialties(self):
        self.stdout.write("Seeding medical specialties and tags...")
        for row in SPECIALTIES:
            upsert_translated(
                MedicalSpecialty,
                slug=row["slug"],
                name_bg=row["bg"],
                name_en=row.get("en"),
                is_active=True,
            )
