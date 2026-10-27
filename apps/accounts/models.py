from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.organizations.models import Organisation


class User(AbstractUser):

    class Role(models.TextChoices):
        OWNER = "OWNER", "Owner"
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        STAFF = "STAFF", "Staff"
        ACCOUNTANT = "ACCOUNTANT", "Accountant"

    email = models.EmailField(unique=True)

    phone = models.CharField(max_length=20, blank=True)

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.STAFF,
    )

    def __str__(self):
        return self.username