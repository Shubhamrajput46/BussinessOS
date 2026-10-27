from django.db import models

from apps.organizations.models import Organisation


class Customer(models.Model):

    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name="customers",
    )

    name = models.CharField(max_length=150)

    email = models.EmailField(blank=True)

    phone = models.CharField(max_length=20)

    address = models.TextField(blank=True)

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name