from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
import base64
import json
from records.models import (
    MedicalCategory,
    MedicalSpecialty,
    DocumentType,
    LabTestMeasurement,
)

class ShareExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="u3", password="p3")
        self.client.login(username="u3", password="p3")
        self.cat = MedicalCategory.objects.create(slug="cat3")
        self.spc = MedicalSpecialty.objects.create(slug="spc3")
        self.dtype = DocumentType.objects.create(slug="type3")
        for obj, name in (
            (self.cat, "Категория"),
            (self.spc, "Специалност"),
            (self.dtype, "Тип документ"),
        ):
            try:
                obj.set_current_language("bg")
                obj.name = name
                obj.save()
            except Exception:
                pass

    def _confirm_doc(self):
        b64 = base64.b64encode(b"x").decode("utf-8")
        analysis = {"summary":"s","data":{"summary":"s","event_date":"2025-09-03","suggested_tags":[],"blood_test_results":[{"indicator_name":"Глюкоза","value":"5.1","unit":"mmol/L","reference_range":"3.9-6.1","measured_at":"2025-09-03T10:00:00"}],"diagnosis":"","treatment_plan":"","doctors":[],"date_created":"2025-09-03"}}
        payload = {"category_id": self.cat.id,"specialty_id": self.spc.id,"doc_type_id": self.dtype.id,"event_id": None,"final_text":"t","final_summary":"s","analysis":analysis,"file_b64":b64,"file_name":"f.pdf","file_mime":"application/pdf","file_kind":"report"}
        res = self.client.post("/api/upload/confirm/", data=json.dumps(payload), content_type="application/json")
        return res.json()

    def test_share_create_history_revoke(self):
        ids = self._confirm_doc()
        doc_id = ids["document_id"]
        res = self.client.post("/api/share/create/", data=json.dumps({"object_type":"document","object_id":doc_id,"scope":"full","format":"html","expire_days":30}), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("ok"))
        token = data.get("token")
        res2 = self.client.get("/api/share/history/")
        self.assertEqual(res2.status_code, 200)
        res3 = self.client.post(f"/api/share/revoke/{token}/")
        self.assertEqual(res3.status_code, 200)

    def test_export_csv(self):
        ids = self._confirm_doc()
        ev_id = ids["event_id"]
        res = self.client.get(f"/api/export/csv/?event_id={ev_id}")
        self.assertEqual(res.status_code, 200)
        body = res.content.decode("utf-8")
        self.assertIn("event_id,event_date,indicator_name,value,unit,reference_low,reference_high,measured_at,tags", body)

    def test_share_filters_return_documents(self):
        ids = self._confirm_doc()
        ev_id = ids["event_id"]
        measurement = LabTestMeasurement.objects.get(medical_event_id=ev_id)
        payload = {
            "start_date": "",
            "end_date": "",
            "hours_events": 12,
            "hours_labs": 12,
            "hours_csv": 12,
            "generate_events": True,
            "generate_labs": True,
            "generate_csv": True,
            "filters": {
                "specialty": [str(self.spc.id)],
                "category": [str(self.cat.id)],
                "event": [str(ev_id)],
                "indicator": [measurement.indicator.slug],
            },
        }
        url = reverse("medj:create_download_links")
        res = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(data["counts"]["documents"], 1)
        self.assertGreaterEqual(data["counts"]["events"], 1)
        self.assertGreaterEqual(data["counts"]["labs"], 1)
        self.assertTrue(data["pdf_events_url"])
        self.assertTrue(data["pdf_labs_url"])
        self.assertTrue(data["csv_url"])
        documents = data.get("documents", [])
        doc_ids = {doc.get("id") for doc in documents}
        self.assertIn(ids["document_id"], doc_ids)
        self.assertTrue(all(doc.get("export_pdf_url") for doc in documents)

        payload["filters"]["event"] = []
        res2 = self.client.post(url, data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res2.status_code, 200)
        data2 = res2.json()
        documents2 = data2.get("documents", [])
        doc_ids2 = {doc.get("id") for doc in documents2}
        self.assertIn(ids["document_id"], doc_ids2)
        self.assertGreaterEqual(data2["counts"]["labs"], 1)
