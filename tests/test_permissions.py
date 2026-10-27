from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import Organisation


class PermissionTest(TestCase):

    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Company",
            email="permission@test.com",
        )

        self.owner = User.objects.create_user(
            username="owner",
            email="owner@test.com",
            password="testpass123",
            organisation=self.organisation,
            role=User.Role.OWNER,
        )

        self.staff = User.objects.create_user(
            username="staff",
            email="staff@test.com",
            password="testpass123",
            organisation=self.organisation,
            role=User.Role.STAFF,
        )

    def test_owner_has_owner_role(self):
        self.assertEqual(
            self.owner.role,
            User.Role.OWNER,
        )

    def test_staff_has_staff_role(self):
        self.assertEqual(
            self.staff.role,
            User.Role.STAFF,
        )

    def test_staff_cannot_access_user_management(self):
        self.client.force_login(self.staff)

        response = self.client.get(
            reverse("user_list")
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(
            response.url,
            reverse("dashboard"),
        )