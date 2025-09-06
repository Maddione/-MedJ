from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
import base64, json
from records.models import MedicalCategory, MedicalSpecialty, DocumentType, MedicalEvent, Document, Tag, DocumentTag

class ConfirmFlowTagTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="u2", password="p2")
        self.client.login(username="u2", password="p2")
        self.cat = MedicalCategory.objects.create(slug="cat2")
        self.spc = MedicalSpecialty.objects.create(slug="spc2")
        self.dtype = DocumentType.objects.create(slug="type2")

    def test_tags_and_inheritance(self):
        b64 = base64.b64encode(b"x").decode("utf-8")
        analysis = {"summary": "s", "data": {"summary":"s","event_date":"2025-09-02","suggested_tags":["custom1","custom2"],"blood_test_results":[],"diagnosis":"","treatment_plan":"","doctors":[],"date_created":"2025-09-02"}}
        payload = {"category_id": self.cat.id,"specialty_id": self.spc.id,"doc_type_id": self.dtype.id,"event_id": None,"final_text": "ocr","final_summary": "sum","analysis": analysis,"file_b64": b64,"file_name": "f.bin","file_mime": "application/octet-stream","file_kind": "note"}
        res = self.client.post("/api/upload/confirm/", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        ev_id = res.json()["event_id"]
        doc_id = res.json()["document_id"]
        doc = Document.objects.get(id=doc_id)
        ev = MedicalEvent.objects.get(id=ev_id)
        self.assertTrue(DocumentTag.objects.filter(document=doc).exists())
        self.assertTrue(ev.tags.exists())
