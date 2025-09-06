from django.test import TestCase, Client
from django.contrib.auth.models import User
import base64, json
from records.models import MedicalCategory, MedicalSpecialty, DocumentType, MedicalEvent

class ShareExportTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username="u3", password="p3")
        self.client.login(username="u3", password="p3")
        self.cat = MedicalCategory.objects.create(slug="cat3")
        self.spc = MedicalSpecialty.objects.create(slug="spc3")
        self.dtype = DocumentType.objects.create(slug="type3")

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
