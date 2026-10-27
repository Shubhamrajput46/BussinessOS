from django.db import models

from apps.organizations.models import Organisation
from apps.products.models import Product
# Create your models here.

class InventoryTransaction(models.Model):
    class TransactionType(models.TextChoices):
        STOCK_IN = "STOCK_IN", "Stock In"
        STOCK_OUT = "STOCK_OUT", "Stock Out"
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"

    organisation=models.ForeignKey(Organisation,on_delete=models.CASCADE,related_name="inventory_transactions")
    product=models.ForeignKey(Product,on_delete=models.CASCADE,related_name="inventory_transactions")
    transaction_type=models.CharField(max_length=20,choices=TransactionType.choices)
    quantity = models.PositiveIntegerField()
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.product.name} - {self.transaction_type}"