from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from records.models import MedicalEvent, MedicalSpecialty, PatientProfile


def create_tx(instance, name_bg, slug):
    instance.set_current_language("bg")
    instance.name = name_bg
    instance.slug = slug
    instance.save()
    return instance


class EventDetailViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="event_user", password="pass123")
        self.client.login(username="event_user", password="pass123")
        self.profile = PatientProfile.objects.create(
            user=self.user,
            first_name_bg="Иван",
            last_name_bg="Иванов",
            date_of_birth=date(1990, 1, 1),
        )
        self.specialty = create_tx(MedicalSpecialty(), "Кардиология", "cardio")
        self.event = MedicalEvent.objects.create(
            patient=self.profile,
            owner=self.user,
            specialty=self.specialty,
            event_date=date(2024, 1, 1),
            summary="Контролен преглед",
        )

    def test_event_detail_view_renders(self):
        response = self.client.get(reverse("medj:medical_event_detail", args=[self.event.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn("medical_event", response.context)
        self.assertEqual(response.context["medical_event"].pk, self.event.pk)
