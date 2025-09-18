from datetime import date
from io import BytesIO

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from records.models import PatientProfile


class PersonalCardLockingTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="card_user", password="pass123")
        self.client.login(username="card_user", password="pass123")
        self.profile = PatientProfile.objects.create(
            user=self.user,
            first_name_bg="Мария",
            last_name_bg="Петрова",
            date_of_birth=date(1992, 5, 20),
        )

    def _base_payload(self):
        return {
            "first_name_bg": "Мария",
            "middle_name_bg": "",
            "last_name_bg": "Иванова",
            "first_name_en": "",
            "middle_name_en": "",
            "last_name_en": "",
            "date_of_birth": "1992-05-20",
            "sex": "female",
            "blood_type": "A+",
            "height_cm": "",
            "weight_kg": "",
            "phone": "",
            "address": "",
        }

    def test_lock_edit_save_cycle(self):
        response = self.client.get(reverse("medj:personalcard"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["profile_locked"])
        self.assertTrue(response.context["editing_allowed"])

        forbidden = self.client.post(reverse("medj:personalcard"), data=self._base_payload())
        self.assertEqual(forbidden.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.last_name_bg, "Петрова")

        payload = self._base_payload()
        payload["editing"] = "1"
        payload["last_name_bg"] = "Иванова"
        success = self.client.post(reverse("medj:personalcard"), data=payload)
        self.assertEqual(success.status_code, 302)
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.last_name_bg, "Иванова")

        final = self.client.get(reverse("medj:personalcard"))
        self.assertEqual(final.status_code, 200)
        self.assertTrue(final.context["profile_locked"])

    def test_qr_endpoint_returns_png(self):
        token = self.profile.ensure_share_token()
        self.profile.share_enabled = True
        self.profile.save(update_fields=["share_enabled"])
        response = self.client.get(reverse("medj:personalcard_qr", args=[token]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "image/png")
        self.assertIn("personal_card.png", response["Content-Disposition"])
        image = Image.open(BytesIO(response.content))
        width, height = image.size
        self.assertGreaterEqual(width, 300)
        self.assertGreaterEqual(height, 300)
