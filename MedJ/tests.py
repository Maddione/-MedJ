import os

import django
from django.test import TestCase, override_settings
from django.urls import reverse

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'settings.dev')
django.setup()


@override_settings(ALLOWED_HOSTS=['testserver'])
class RegistrationViewTests(TestCase):
    def test_registration_page_loads(self):
        response = self.client.get(reverse('medj:register'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('Регистрация', response.content.decode())


@override_settings(ALLOWED_HOSTS=['testserver'])
class LandingPageTests(TestCase):
    def test_landing_page_loads(self):
        response = self.client.get(reverse('medj:landingpage'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('MedJ', response.content.decode())
