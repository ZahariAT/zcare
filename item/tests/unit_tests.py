from rest_framework.test import APITestCase, APIRequestFactory
from rest_framework.exceptions import ValidationError
from django.test import TestCase
from unittest.mock import patch
from decimal import Decimal

from core.models import Account
from item.views import *
from item.models import *
from item.serializers import *
from item.search import *
from item.permissions import IsStuffOrReadOnly


class SearchIntegrationTests(APITestCase):
    def setUp(self):
        self.category = Category.objects.create(
            name='Medicine'
        )

        # Create sample items
        self.aspirin = Item.objects.create(name="Aspirin", description="Pain reliever",
                                           category=self.category,
                                           price=2.20,
                                           quantity=1000,
                                           is_with_prescription=False
                                           )
        self.ibuprofen = Item.objects.create(name="Ibuprofen", description="Headache medicine",
                                             category=self.category,
                                             price=2.20,
                                             quantity=1000,
                                             is_with_prescription=False
                                             )
        self.tylenol = Item.objects.create(name="Tylenol", description="Fast acting pain relief",
                                           category=self.category,
                                           price=2.20,
                                           quantity=1000,
                                           is_with_prescription=False
                                           )

    # unit tests perform_nlp_search
    def test_basic_query_description(self):
        results = perform_nlp_search("pain reliever")
        self.assertIn("Aspirin", [result.name for result in results])

    def test_basic_query_name(self):
        results = perform_nlp_search("Aspirin")
        self.assertIn("Aspirin", [result.name for result in results])

    def test_basic_query_category(self):
        results = perform_nlp_search("Medicine")
        self.assertIn("Aspirin", [result.name for result in results])

    def test_synonym_query(self):
        results = perform_nlp_search("head hurts")
        self.assertIn("Ibuprofen", [result.name for result in results])

    def test_misspelled_query_by_description(self):
        results = perform_nlp_search("payn relivr")
        self.assertIn("Aspirin", [result.name for result in results])
        self.assertIn("Tylenol", [result.name for result in results])

    def test_misspelled_query_by_name(self):
        results = perform_nlp_search("aspirn")
        self.assertIn("Aspirin", [result.name for result in results])

    def test_misspelled_query_by_category(self):
        results = perform_nlp_search("medcin")
        self.assertIn("Aspirin", [result.name for result in results])

    def test_phrase_query(self):
        results = perform_nlp_search("fast acting pain relief")
        self.assertIn("Tylenol", [result.name for result in results])

    def test_search_no_matches(self):
        # Search that should return no results
        query = "antihistamine"
        results = perform_nlp_search(query)
        self.assertEqual(len(results), 0)

    def test_search_with_special_characters(self):
        # Search with special characters
        query = "Ibuprofen!"
        results = perform_nlp_search(query)
        self.assertIn(self.ibuprofen, results)
        self.assertEqual(len(results), 1)

    def test_search_ignore_case(self):
        # Case-insensitive search
        query = "ibuproFEN"
        results = perform_nlp_search(query)
        self.assertIn(self.ibuprofen, results)
        self.assertEqual(len(results), 1)

    # unit tests for correct_text
    def test_misspelled_query_by_payn_relivr(self):
        result = correct_text("payn relivr")
        self.assertEquals(result, 'pain relive')

    def test_misspelled_query_by_ibuproFEN(self):
        result = correct_text("aspirn")
        self.assertEquals(result, 'aspirin')

    def test_misspelled_medcin(self):
        result = correct_text("medcin")
        self.assertEquals(result, 'medicine')

    # unit test preprocess_query
    def test_preprocess_query_medicine(self):
        result = preprocess_query("medicines")
        self.assertEquals(result, 'medicine')

    def test_preprocess_query_aspirin(self):
        result = preprocess_query("headache")
        self.assertEquals(result, 'headache')

    def test_preprocess_query_pain_reliever(self):
        result = preprocess_query("relieves pains")
        self.assertEquals(result, 'relief pain')

    # unit test perform_search
    def test_perform_search_by_query(self):
        query = 'pain hurting hurt projected anguish take over save painfulness let off jutting salvage projecting eased nuisance lighten protruding ail alleviated ease sticking out allay still sticking pain sensation botheration exempt pain in the ass alleviate salve relieve remedy pain in the neck excuse unbosom painful sensation free relieved bother palliate assuage infliction annoyance trouble'
        result = perform_search(query)
        self.assertIn(self.aspirin, result)
        self.assertIn(self.tylenol, result)

    def test_perform_search_by_category(self):
        category_herbs = Category.objects.create(
            name='Herbs'
        )
        mint = Item.objects.create(name="Mint", description="Relieves pain in the throat",
                                   category=category_herbs,
                                   price=2.20,
                                   quantity=1000,
                                   is_with_prescription=False
                                   )
        query = category_herbs.name.lower()
        result = perform_search(query)
        self.assertIn(mint, result)

    def test_perform_search_by_name(self):
        query = self.aspirin.name.lower()
        result = perform_search(query)
        self.assertIn(self.aspirin, result)

    def test_perform_search_by_description(self):
        query = self.aspirin.description.lower()
        result = perform_search(query)
        self.assertIn(self.aspirin, result)

    def test_perform_search_empty(self):
        query = 'das auto'
        result = perform_search(query)
        self.assertEquals([], result)

    # unit test expand_query_with_synonyms
    def test_expand_query_with_synonyms_by_new_word(self):
        query = 'headache'
        result = expand_query_with_synonyms(query)
        self.assertIn('headache', result)
        self.assertIn('head', result)
        self.assertIn('ache', result)

    def test_expand_query_with_synonyms_from_custom_synonyms(self):
        query = 'painkiller'
        result = expand_query_with_synonyms(query)
        self.assertIn('analgesic', result)
        self.assertIn('pain reliever', result)
        self.assertIn('pain relief medication', result)

    def test_expand_query_with_synonyms_from_no_synonyms(self):
        query = 'analgin'
        result = expand_query_with_synonyms(query)
        self.assertEquals('analgin', result)

    # unit test expand_query_with_synonyms
    def test_semantic_search_by_new_word(self):
        query = 'Pain reliever'
        result = semantic_search(query, [self.aspirin, self.ibuprofen])
        self.assertEquals(result[0], self.aspirin)
        self.assertEquals(result[1], self.ibuprofen)


class ItemViewSetTests(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = ItemViewSet.as_view({'get': 'list'})

    @patch('item.views.Item.objects.all')
    def test_get_queryset(self, mock_get_queryset):
        request = self.factory.get('/')
        mock_get_queryset.return_value = Item.objects.none()
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


class ItemSerializerTests(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(name='Health')
        self.item = Item.objects.create(
            category=self.category,
            name='Painkiller',
            description='Pain relief medicine',
            price=10.0,
            quantity=100,
            is_with_prescription=False
        )

    def test_item_serialization(self):
        serializer = ItemSerializer(self.item)
        data = serializer.data
        self.assertEqual(set(data.keys()),
                         {'id', 'category', 'name', 'description', 'price', 'quantity', 'image', 'updated_at',
                          'is_with_prescription'})

    def test_item_deserialization(self):
        data = {
            'category': self.category.id,
            'name': 'Painkiller',
            'description': 'Pain relief medicine',
            'price': 10.0,
            'quantity': 100,
            'is_with_prescription': False
        }
        serializer = ItemSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        item = serializer.save()
        self.assertEqual(item.name, 'Painkiller')


class ItemModelTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name='Health')
        self.item = Item.objects.create(
            category=self.category,
            name='Painkiller',
            description='Pain relief medicine',
            price=10.0,
            quantity=100,
            is_with_prescription=False
        )

    def test_item_creation(self):
        item = Item.objects.create(
            name='Test Item',
            description='A test item description',
            price=19.99,
            quantity=100,
            category=self.category,
            is_with_prescription=False,
        )

        self.assertEqual(item.name, 'Test Item')
        self.assertEqual(item.description, 'A test item description')
        self.assertEqual(item.price, 19.99)
        self.assertEqual(item.quantity, 100)
        self.assertEqual(item.category, self.category)
        self.assertFalse(item.is_with_prescription)

        self.assertTrue(Item.objects.filter(name='Test Item').exists())

    def test_item_str_method(self):
        self.assertEqual(str(self.item), 'Painkiller')


class IsStuffOrReadOnlyTests(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.permission = IsStuffOrReadOnly()

        # Create a staff user
        self.password = 'password'
        self.staff_user = Account.objects.create_pharmacist(
            email='staffuser@example.com', password=self.password, name='staffuser'
        )

        # Create a non-staff user
        self.non_staff_user = Account.objects.create_user(
            email='nonstaffuser@example.com', password=self.password, name='nonstaffuser'
        )

        # Create an unauthenticated request
        self.unauthenticated_request = self.factory.get('/')
        self.unauthenticated_request.user = None

    def test_permission_allows_staff_user(self):
        request = self.factory.get('/')
        request.user = self.staff_user
        self.assertTrue(self.permission.has_permission(request, None))

    def test_permission_denies_non_staff_user_for_write(self):
        request = self.factory.post('/')
        request.user = self.non_staff_user
        self.assertFalse(self.permission.has_permission(request, None))

    def test_permission_allows_non_staff_user_for_read(self):
        request = self.factory.get('/')
        request.user = self.non_staff_user
        self.assertTrue(self.permission.has_permission(request, None))

    def test_permission_denies_unauthenticated_user_for_write(self):
        request = self.factory.post('/')
        request.user = None
        self.assertFalse(self.permission.has_permission(request, None))

    def test_permission_allows_unauthenticated_user_for_read(self):
        request = self.factory.get('/')
        request.user = None
        self.assertTrue(self.permission.has_permission(request, None))


class CategoryModelTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name='Health')

    def test_category_creation(self):
        category = Category.objects.create(name='Test Category')

        self.assertEqual(category.name, 'Test Category')

        self.assertTrue(Category.objects.filter(name='Test Category').exists())

    def test_category_str(self):
        self.assertEqual(str(self.category), 'Health')


class CategorySerializerTests(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(name='Health')

    def test_category_serialization(self):
        serializer = CategorySerializer(self.category)
        data = serializer.data
        self.assertEqual(set(data.keys()), set(['id', 'name']))

    def test_category_deserialization(self):
        data = {
            'name': 'Pharmacy'
        }
        serializer = CategorySerializer(data=data)
        self.assertTrue(serializer.is_valid())
        category = serializer.save()
        self.assertEqual(category.name, 'Pharmacy')


class CategoryViewSetTests(APITestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.view = CategoryViewSet.as_view({'get': 'list'})

    @patch('item.views.Category.objects.all')
    def test_get_queryset(self, mock_get_queryset):
        request = self.factory.get('/')
        mock_get_queryset.return_value = Category.objects.none()
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 0)


class BusinessStatisticsSerializerTests(TestCase):

    def test_valid_data(self):
        data = {
            'total_sales': '1000.00',
            'total_orders': 10,
            'revenue_by_category': {'Category1': '500.00', 'Category2': '500.00'},
            'average_order_value': '100.00',
            'top_selling_products': [
                {'id': 1, 'name': 'Product 1', 'total_quantity': 50},
                {'id': 2, 'name': 'Product 2', 'total_quantity': 30},
            ],
        }
        expected_data = {
            'total_sales': Decimal('1000.00'),
            'total_orders': 10,
            'revenue_by_category': {'Category1': Decimal('500.00'), 'Category2': Decimal('500.00')},
            'average_order_value': Decimal('100.00'),
            'top_selling_products': [
                {'id': 1, 'name': 'Product 1', 'total_quantity': 50},
                {'id': 2, 'name': 'Product 2', 'total_quantity': 30},
            ],
        }
        serializer = BusinessStatisticsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, expected_data)

    def test_invalid_total_sales(self):
        data = {
            'total_sales': 'invalid',
            'total_orders': 10,
            'revenue_by_category': {'Category1': '500.00', 'Category2': '500.00'},
            'average_order_value': '100.00',
            'top_selling_products': [
                {'id': 1, 'name': 'Product 1', 'total_quantity': 50},
                {'id': 2, 'name': 'Product 2', 'total_quantity': 30},
            ],
        }
        serializer = BusinessStatisticsSerializer(data=data)
        with self.assertRaises(ValidationError):
            serializer.is_valid(raise_exception=True)

    def test_empty_top_selling_products(self):
        data = {
            'total_sales': '1000.00',
            'total_orders': 10,
            'revenue_by_category': {'Category1': '500.00', 'Category2': '500.00'},
            'average_order_value': '100.00',
            'top_selling_products': [],
        }
        expected_data = {
            'total_sales': Decimal('1000.00'),
            'total_orders': 10,
            'revenue_by_category': {'Category1': Decimal('500.00'), 'Category2': Decimal('500.00')},
            'average_order_value': Decimal('100.00'),
            'top_selling_products': [],
        }
        serializer = BusinessStatisticsSerializer(data=data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data, expected_data)


class OrderModelTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name="Category1")
        self.item = Item.objects.create(
            name="Item1",
            category=self.category,
            price=Decimal('10.00'),
            quantity=100
        )
        self.user = Account.objects.create_user(
            email='user@example.com',
            name='Test User',
            password='password123'
        )
        self.order = Order.objects.create(
            item=self.item,
            user=self.user,
            total_price=Decimal('100.00'),
            quantity=10
        )

    def test_order_creation(self):
        order = Order.objects.create(
            item=self.item,
            user=self.user,
            total_price=Decimal('50.00'),
            quantity=5
        )
        self.assertEqual(order.item, self.item)
        self.assertEqual(order.user, self.user)
        self.assertEqual(order.total_price, Decimal('50.00'))
        self.assertEqual(order.quantity, 5)

    def test_order_str_method(self):
        self.assertEqual(str(self.order),
                         f'Order by {self.user} for {self.order.quantity} of {self.item} on {self.order.order_date}')


class OrderSerializerTests(TestCase):

    def setUp(self):
        self.category = Category.objects.create(name="Category1")
        self.item = Item.objects.create(
            name="Item1",
            category=self.category,
            price=Decimal('10.00'),
            quantity=100
        )
        self.user = Account.objects.create_user(
            email='user@example.com',
            name='Test User',
            password='password123'
        )
        self.order = Order.objects.create(
            item=self.item,
            user=self.user,
            total_price=Decimal('100.00'),
            quantity=10
        )
        self.serializer = OrderSerializer(instance=self.order)

    def test_serializer_contains_expected_fields(self):
        data = self.serializer.data
        self.assertEqual(set(data.keys()), set(['item', 'user', 'total_price', 'quantity', 'order_date']))

    def test_serializer_field_content(self):
        data = self.serializer.data
        expected_date = str(self.order.order_date).split('+')[0].split(' ')
        self.assertEqual(data['item'], self.order.item.id)
        self.assertEqual(data['user'], self.order.user.email)
        self.assertEqual(data['total_price'], '100.00')
        self.assertEqual(data['quantity'], 10)
        self.assertIn(expected_date[0], data['order_date'])
        self.assertIn(expected_date[1], data['order_date'])
