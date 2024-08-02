from rest_framework import serializers

from .models import Item, Category, Order


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Item
        fields = '__all__'


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['item', 'user', 'total_price', 'quantity', 'order_date']


class BusinessStatisticsSerializer(serializers.Serializer):
    total_sales = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_orders = serializers.IntegerField()
    revenue_by_category = serializers.DictField(child=serializers.DecimalField(max_digits=10, decimal_places=2))
    average_order_value = serializers.DecimalField(max_digits=10, decimal_places=2)
    top_selling_products = serializers.ListField(child=serializers.DictField())
