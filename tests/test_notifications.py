from django.test import TestCase

from apps.accounts.models import User
from apps.notifications.models import Notification
from apps.organizations.models import Organisation


class NotificationModelTest(TestCase):

    def setUp(self):
        self.organisation = Organisation.objects.create(
            name="Test Company",
            email="test@company.com",
        )

        self.user = User.objects.create_user(
            username="testuser",
            email="user@company.com",
            password="testpass123",
            organisation=self.organisation,
        )

    def test_notification_created(self):
        notification = Notification.objects.create(
            organisation=self.organisation,
            user=self.user,
            title="Welcome",
            message="Welcome to BusinessOS",
        )

        self.assertEqual(notification.title, "Welcome")
        self.assertEqual(notification.message, "Welcome to BusinessOS")

    def test_notification_belongs_to_organisation(self):
        notification = Notification.objects.create(
            organisation=self.organisation,
            user=self.user,
            title="Stock Alert",
            message="Product stock is low",
        )

        self.assertEqual(
            notification.organisation,
            self.organisation,
        )

    def test_notification_belongs_to_user(self):
        notification = Notification.objects.create(
            organisation=self.organisation,
            user=self.user,
            title="Order Update",
            message="Your order has been completed",
        )

        self.assertEqual(notification.user, self.user)

    def test_default_notification_type_is_info(self):
        notification = Notification.objects.create(
            organisation=self.organisation,
            user=self.user,
            title="Information",
            message="This is an information notification",
        )

        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.INFO,
        )

    def test_notification_is_unread_by_default(self):
        notification = Notification.objects.create(
            organisation=self.organisation,
            user=self.user,
            title="New Notification",
            message="You have a new notification",
        )

        self.assertFalse(notification.is_read)

    def test_notification_can_be_marked_as_read(self):
        notification = Notification.objects.create(
            organisation=self.organisation,
            user=self.user,
            title="Read Notification",
            message="This notification is now read",
        )

        notification.is_read = True
        notification.save()

        notification.refresh_from_db()

        self.assertTrue(notification.is_read)