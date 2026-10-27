from django.db import models

from apps.organizations.models import Organisation
from apps.accounts.models import User


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        INFO = "INFO", "Information"
        SUCCESS = "SUCCESS", "Success"
        WARNING = "WARNING", "Warning"
        ERROR = "ERROR", "Error"

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    title = models.CharField(max_length=150)

    message = models.TextField()

    notification_type = models.CharField(
        max_length=20,
        choices=NotificationType.choices,
        default=NotificationType.INFO,
    )

    is_read = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title