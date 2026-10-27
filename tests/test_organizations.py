from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organisation


class OrganisationIsolationTest(TestCase):

    def setUp(self):
        self.org1 = Organisation.objects.create(
            name="Company One",
            email="company1@test.com",
        )

        self.org2 = Organisation.objects.create(
            name="Company Two",
            email="company2@test.com",
        )

        self.user1 = User.objects.create_user(
            username="user1",
            email="user1@test.com",
            password="testpass123",
            organisation=self.org1,
            role=User.Role.OWNER,
        )

        self.user2 = User.objects.create_user(
            username="user2",
            email="user2@test.com",
            password="testpass123",
            organisation=self.org2,
            role=User.Role.OWNER,
        )

    def test_user_belongs_to_correct_organisation(self):
        self.assertEqual(
            self.user1.organisation,
            self.org1,
        )

        self.assertEqual(
            self.user2.organisation,
            self.org2,
        )

    def test_organisation_has_only_its_users(self):
        org1_users = User.objects.filter(
            organisation=self.org1
        )

        org2_users = User.objects.filter(
            organisation=self.org2
        )

        self.assertEqual(org1_users.count(), 1)
        self.assertEqual(org2_users.count(), 1)

        self.assertIn(self.user1, org1_users)
        self.assertNotIn(self.user2, org1_users)

        self.assertIn(self.user2, org2_users)
        self.assertNotIn(self.user1, org2_users)