from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
import base64
import json
from records.models import MedicalCategory, MedicalSpecialty, DocumentType, MedicalEvent, Document, LabTestMeasurement

class UploadFlowTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="u1", password="p1")
        self.client.login(username="u1", password="p1")
        self.cat = MedicalCategory.objects.create(slug="cat1")
        try:
            self.cat.set_current_language("bg")
            self.cat.name = "Категория"
            self.cat.save()
        except Exception:
            pass
        self.spc = MedicalSpecialty.objects.create(slug="spc1")
        try:
            self.spc.set_current_language("bg")
            self.spc.name = "Специалност"
            self.spc.save()
        except Exception:
            pass
        self.dtype = DocumentType.objects.create(slug="type1")
        try:
            self.dtype.set_current_language("bg")
            self.dtype.name = "Тип"
            self.dtype.save()
        except Exception:
            pass

    def test_ocr_endpoint_minimal(self):
        f = SimpleUploadedFile("t.txt", b"abc", content_type="text/plain")
        res = self.client.post("/api/upload/ocr/", {"file": f, "file_kind": "report", "category_id": self.cat.id, "specialty_id": self.spc.id, "doc_type_id": self.dtype.id})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("ocr_text", data)
        self.assertIn("source", data)

    def test_analyze_endpoint_schema(self):
        payload = {"text": "Тестов текст", "specialty_id": self.spc.id}
        res = self.client.post("/api/upload/analyze/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("data", data)
        self.assertIn("summary", data)

    def test_confirm_creates_event_document_and_labs(self):
        content = b"PDF"
        b64 = base64.b64encode(content).decode("utf-8")
        analysis = {
            "summary": "s",
            "data": {
                "summary": "s",
                "event_date": "2025-09-01",
                "detected_specialty": "spc",
                "suggested_tags": ["тест"],
                "blood_test_results": [
                    {"indicator_name":"Хемоглобин","value":"120","unit":"g/L","reference_range":"115-155","measured_at":"2025-09-01T12:00:00"}
                ],
                "diagnosis": "",
                "treatment_plan": "",
                "doctors": [],
                "date_created": "2025-09-01"
            }
        }
        payload = {
            "category_id": self.cat.id,
            "specialty_id": self.spc.id,
            "doc_type_id": self.dtype.id,
            "event_id": None,
            "final_text": "ocr",
            "final_summary": "sum",
            "analysis": analysis,
            "file_b64": b64,
            "file_name": "a.pdf",
            "file_mime": "application/pdf",
            "file_kind": "report"
        }
        res = self.client.post("/api/upload/confirm/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        self.assertTrue(MedicalEvent.objects.filter(id=data["event_id"]).exists())
        self.assertTrue(Document.objects.filter(id=data["document_id"]).exists())
        self.assertTrue(LabTestMeasurement.objects.filter(medical_event_id=data["event_id"]).exists())

    def test_events_suggest(self):
        ev = MedicalEvent.objects.create(patient=self.user.patientprofile, owner=self.user, category=self.cat, specialty=self.spc, doc_type=self.dtype, event_date="2025-09-01")
        res = self.client.get(f"/api/events/suggest/?category_id={self.cat.id}&specialty_id={self.spc.id}&doc_type_id={self.dtype.id}")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("events", data)
        self.assertTrue(any(str(it.get("id")) == str(ev.id) for it in data["events"]))

    def _confirm_with_file(self, payload_bytes, summary="sum", extra=None):
        file_obj = SimpleUploadedFile("sample.pdf", payload_bytes, content_type="application/pdf")
        data = {
            "file": file_obj,
            "file_kind": "pdf",
            "category_id": self.cat.id,
            "specialty_id": self.spc.id,
            "doc_type_id": self.dtype.id,
            "ocr_text": "ocr",
            "text": "ocr",
            "summary": summary,
        }
        if extra:
            data.update(extra)
        return self.client.post("/api/upload/confirm/", data=data)

    def test_confirm_duplicate_conflict(self):
        payload = b"duplicate-content"
        first = self._confirm_with_file(payload, summary="first")
        self.assertEqual(first.status_code, 200)
        self.assertEqual(Document.objects.count(), 1)
        again = self._confirm_with_file(payload, summary="second")
        self.assertEqual(again.status_code, 409)
        body = again.json()
        self.assertEqual(body.get("error"), "duplicate")
        self.assertEqual(Document.objects.count(), 1)

    def test_confirm_sets_creation_date_fallback(self):
        payload = b"date-check"
        res = self._confirm_with_file(payload, summary="custom summary")
        self.assertEqual(res.status_code, 200)
        doc = Document.objects.order_by("-id").first()
        self.assertIsNotNone(doc)
        self.assertIsNotNone(doc.date_created)
        self.assertIsNotNone(doc.uploaded_at)
        self.assertEqual(doc.date_created, doc.uploaded_at.date())
        self.assertEqual(doc.summary, "custom summary")
        self.assertTrue(doc.content_hash)
