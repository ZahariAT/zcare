from django_filters import rest_framework as filters
from .models import Order


class OrderFilter(filters.FilterSet):
    order_date_after = filters.DateTimeFilter(field_name="order_date", lookup_expr='gte')

    class Meta:
        model = Order
        fields = ['order_date_after']
