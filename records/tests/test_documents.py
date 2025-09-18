from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from records.models import (
    Document,
    DocumentType,
    MedicalCategory,
    MedicalEvent,
    MedicalSpecialty,
    PatientProfile,
)


def create_tx(instance, name_bg, slug):
    instance.set_current_language("bg")
    instance.name = name_bg
    instance.slug = slug
    instance.save()
    return instance


class DocumentRoutingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="docs", password="pass123")
        self.client.login(username="docs", password="pass123")
        self.profile = PatientProfile.objects.create(
            user=self.user,
            first_name_bg="Анна",
            last_name_bg="Иванова",
            date_of_birth="1990-01-01",
        )
        self.specialty = create_tx(MedicalSpecialty(), "Кардиология", "cardio")
        self.category = create_tx(MedicalCategory(), "Документи", "cat")
        self.doc_type = create_tx(DocumentType(), "Епикриза", "report")
        self.event = MedicalEvent.objects.create(
            patient=self.profile,
            owner=self.user,
            specialty=self.specialty,
            category=self.category,
            doc_type=self.doc_type,
            event_date="2024-01-01",
            summary="Ехокардиография",
        )
        self.document = Document.objects.create(
            owner=self.user,
            medical_event=self.event,
            specialty=self.specialty,
            category=self.category,
            doc_type=self.doc_type,
            document_date="2024-01-02",
            file=SimpleUploadedFile("report.pdf", b"test", content_type="application/pdf"),
        )

    def test_documents_list_contains_detail_link(self):
        response = self.client.get(reverse("medj:documents"))
        self.assertEqual(response.status_code, 200)
        detail_url = reverse("medj:document_detail", args=[self.document.pk])
        self.assertIn(detail_url.encode(), response.content)

    def test_document_detail_renders(self):
        response = self.client.get(reverse("medj:document_detail", args=[self.document.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("document", response.context)
        self.assertEqual(response.context["document"].pk, self.document.pk)
