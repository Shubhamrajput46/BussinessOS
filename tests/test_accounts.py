from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import Organisation


class LoginTest(TestCase):

    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Company",
            email="testcompany@test.com",
        )

        self.user = User.objects.create_user(
            username="testuser",
            email="testuser@test.com",
            password="testpass123",
            organisation=self.organisation,
            role=User.Role.OWNER,
        )

    def test_login_page_loads(self):
        response = self.client.get(reverse("login"))

        self.assertEqual(response.status_code, 200)

    def test_user_can_login(self):
        response = self.client.post(
            reverse("login"),
            {
                "email": "testuser@test.com",
                "password": "testpass123",
            },
        )

        self.assertEqual(response.status_code, 302)

    def test_invalid_login_fails(self):
        response = self.client.post(
            reverse("login"),
            {
                "email": "testuser@test.com",
                "password": "wrongpassword",
            },
        )

        self.assertEqual(response.status_code, 200)