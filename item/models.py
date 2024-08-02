from django.core.validators import BaseValidator
from django.db import models

from core.models import Account


class MinValueValidator(BaseValidator):
    message = 'Ensure this value is greater than or equal to %(limit_value)s.'
    code = 'min_value'

    def compare(self, a, b):
        return a < b


class Category(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name


class Item(models.Model):
    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    price = models.FloatField()
    image = models.ImageField(upload_to='item_images', blank=True, null=True)
    quantity = models.IntegerField(default=0, null=False, validators=[MinValueValidator(0)])
    updated_at = models.DateTimeField(auto_now_add=True)
    is_with_prescription = models.BooleanField(default=False)

    def __str__(self):
        return self.name


class Order(models.Model):
    item = models.ForeignKey(Item, related_name='item', on_delete=models.PROTECT)
    user = models.ForeignKey(Account, related_name='user', on_delete=models.PROTECT, to_field='email')
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    order_date = models.DateTimeField(verbose_name='order_date', auto_now_add=True)

    def __str__(self):
        return f'Order by {self.user} for {self.quantity} of {self.item} on {self.order_date}'
