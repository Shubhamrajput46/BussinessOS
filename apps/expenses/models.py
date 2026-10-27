from django.db import models
from apps.organizations.models import Organisation
# Create your models here.
class Expense(models.Model):
    class Category(models.TextChoices):
        RENT="RENT","Rent"
        SALARY="SALARY","Salary"
        ELECTRICITY = "ELECTRICITY", "Electricity"
        TRANSPORT = "TRANSPORT", "Transport"
        MARKETING = "MARKETING", "Marketing"
        OFFICE = "OFFICE", "Office"
        MAINTENANCE = "MAINTENANCE", "Maintenance"
        OTHER = "OTHER", "Other"

    organisation=models.ForeignKey(Organisation,on_delete=models.CASCADE,related_name="expense")
    title = models.CharField(max_length=150)

    category = models.CharField(
        max_length=30,
        choices=Category.choices,
    )

    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
    )

    description = models.TextField(blank=True)

    expense_date = models.DateField()

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title