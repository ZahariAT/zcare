from rest_framework import permissions, viewsets, status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Sum, Avg
from django.contrib.auth import get_user_model

from .serializers import ItemSerializer, CategorySerializer, OrderSerializer, BusinessStatisticsSerializer
from .models import Item, Category, Order
from .filters import OrderFilter
from .permissions import IsStuffOrReadOnly, IsAdmin
from .search import perform_nlp_search


class CategoryViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows categories to be viewed or edited.
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsStuffOrReadOnly]


class ItemViewSet(viewsets.ModelViewSet):
    """
    API endpoint that allows items to be viewed or edited.
    """
    queryset = Item.objects.all()
    serializer_class = ItemSerializer
    permission_classes = [IsStuffOrReadOnly]


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def item_buy(request, pk):
    res_status = status.HTTP_400_BAD_REQUEST
    message = 'Item can\'t be found!'

    items = Item.objects.filter(pk=pk)
    item = None
    related_items = []
    if items:
        item = items[0]
        related_items = Item.objects.filter(category=item.category).exclude(pk=pk)[0:3]
        related_items = ItemSerializer(data=related_items, many=True)
        related_items.is_valid()
        related_items = related_items.data
        message = 'Item is with prescription and can\'t be bought online!'

    if item and not item.is_with_prescription:
        old_quantity = item.quantity
        data = request.data
        buy_quantity = int(data['quantity'])
        if not buy_quantity > 0:
            message = f'Can\'t buy 0 products.'
            res_status = status.HTTP_400_BAD_REQUEST
        elif old_quantity - buy_quantity < 0:
            message = f'Not enough of the product. Currently available - {old_quantity}!'
            res_status = status.HTTP_400_BAD_REQUEST
        else:
            item.quantity = old_quantity - buy_quantity
            item.save()
            total_price = buy_quantity * item.price
            message = f'Bought {buy_quantity} items for {total_price}.'
            res_status = status.HTTP_200_OK
            user = request.user if request.user.is_authenticated else get_user_model().objects.get(
                email='anonymous@example.com')
            Order(item=item, user=user, quantity=buy_quantity, total_price=total_price).save()

    return Response({
        'related_items': related_items,
        'message': message
    }, status=res_status)


class OrderHistoryView(generics.ListAPIView):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):
        queryset = Order.objects.filter(user=self.request.user).order_by('-order_date')
        quantity = int(self.request.query_params.get('quantity', 0))
        if quantity:
            queryset = queryset[0:quantity]

        return queryset


class BusinessStatisticsView(APIView):
    permission_classes = [IsAdmin]

    def get(self, request, *args, **kwargs):
        total_sales = Order.objects.aggregate(total=Sum('total_price'))['total'] or 0

        total_orders = Order.objects.count()

        revenue_by_category = Order.objects.values('item__category').annotate(
            revenue=Sum('total_price')
        )
        revenue_by_category = {item['item__category']: item['revenue'] for item in revenue_by_category}

        average_order_value = Order.objects.aggregate(avg=Avg('total_price'))['avg'] or 0

        top_selling_products = Order.objects.values('item__id', 'item__name').annotate(
            total_quantity=Sum('quantity')
        ).order_by('-total_quantity')[:5]
        top_selling_products = [
            {'id': item['item__id'], 'name': item['item__name'], 'total_quantity': item['total_quantity']}
            for item in top_selling_products
        ]

        data = {
            'total_sales': total_sales,
            'total_orders': total_orders,
            'revenue_by_category': revenue_by_category,
            'average_order_value': average_order_value,
            'top_selling_products': top_selling_products,
        }

        serializer = BusinessStatisticsSerializer(data)
        return Response(serializer.data)


class CorrectedItemSearchView(APIView):
    def get(self, request, *args, **kwargs):
        query = request.GET.get('q', '')
        search_results = perform_nlp_search(query)
        serializer = ItemSerializer(search_results, many=True)
        return Response(serializer.data)
