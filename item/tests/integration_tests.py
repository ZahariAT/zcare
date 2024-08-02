from decimal import Decimal

from rest_framework.test import APITestCase
from django.urls import reverse
from rest_framework import status
from django.contrib.auth import get_user_model

from core.models import Account
from item.views import *
from item.models import *
from item.search import *

User = get_user_model()


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

    def test_search_api(self):
        response = self.client.get(reverse('item-search'), {'q': 'pain reliever'})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Aspirin", [result['name'] for result in response.json()])
        self.assertIn("Tylenol", [result['name'] for result in response.json()])

    def test_search_ordering(self):
        response = self.client.get(reverse('item-search'), {'q': 'pain relief'})
        self.assertEqual(response.status_code, 200)
        results = response.json()

        self.assertEquals(results[0]['name'], 'Tylenol')
        self.assertEquals(results[1]['name'], 'Aspirin')


class CategoryIntegrationTests(APITestCase):

    def setUp(self):
        # Create a staff user
        self.password = 'password'
        self.staff_user = Account.objects.create_pharmacist(
            email='staffuser@example.com', password=self.password, name='staffuser'
        )

        # Create a non-staff user
        self.non_staff_user = Account.objects.create_user(
            email='nonstaffuser@example.com', password=self.password, name='nonstaffuser'
        )

        # Create some categories
        self.category1 = Category.objects.create(name='Category 1')
        self.category2 = Category.objects.create(name='Category 2')

        # Define the API endpoints
        self.url = reverse('category-list')
        self.login_url = reverse('login')

    def test_unauthenticated_user_can_view_categories(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_user_cannot_create_category(self):
        response = self.client.post(self.url, {'name': 'New Category'})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_staff_user_can_view_categories(self):
        token = \
            self.client.post(self.login_url,
                             data={'email': self.non_staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_non_staff_user_cannot_create_category(self):
        token = \
            self.client.post(self.login_url,
                             data={'email': self.non_staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.url, {'name': 'New Category'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_category(self):
        token = \
            self.client.post(self.login_url, data={'email': self.staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.url, {'name': 'New Category'})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Category.objects.count(), 3)

    def test_staff_user_can_update_category(self):
        token = \
            self.client.post(self.login_url, data={'email': self.staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('category-detail', args=[self.category1.id])
        response = self.client.put(url, {'name': 'Updated Category'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.category1.refresh_from_db()
        self.assertEqual(self.category1.name, 'Updated Category')

    def test_staff_user_can_delete_category(self):
        token = \
            self.client.post(self.login_url, data={'email': self.staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('category-detail', args=[self.category1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Category.objects.count(), 1)

    def test_non_staff_user_cannot_update_category(self):
        token = \
            self.client.post(self.login_url,
                             data={'email': self.non_staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('category-detail', args=[self.category1.id])
        response = self.client.put(url, {'name': 'Updated Category'})
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_user_cannot_delete_category(self):
        token = \
            self.client.post(self.login_url,
                             data={'email': self.non_staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('category-detail', args=[self.category1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ItemIntegrationTests(APITestCase):
    def setUp(self):
        # Create a staff user
        self.password = 'password'
        self.staff_user = Account.objects.create_pharmacist(
            email='staffuser@example.com', password=self.password, name='staffuser'
        )

        # Create a non-staff user
        self.non_staff_user = Account.objects.create_user(
            email='nonstaffuser@example.com', password=self.password, name='nonstaffuser'
        )

        # Create a category
        self.category = Category.objects.create(name='Health')

        # Create some items
        self.item1 = Item.objects.create(
            category=self.category,
            name='Painkiller',
            description='Pain relief medicine',
            price=10.0,
            quantity=100,
            is_with_prescription=False
        )
        self.item2 = Item.objects.create(
            category=self.category,
            name='Antibiotic',
            description='Used for bacterial infections',
            price=25.0,
            quantity=50,
            is_with_prescription=True
        )

        # Define the API endpoints
        self.url = reverse('item-list')
        self.login_url = reverse('login')

    def test_unauthenticated_user_can_view_items(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_unauthenticated_user_cannot_create_item(self):
        response = self.client.post(self.url, {
            'name': 'New Item',
            'description': 'Description',
            'price': 15.0,
            'quantity': 30,
            'category': self.category.id,
            'is_with_prescription': False
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_staff_user_can_view_items(self):
        token = \
            self.client.post(self.login_url,
                             data={'email': self.non_staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_non_staff_user_cannot_create_item(self):
        token = \
            self.client.post(self.login_url,
                             data={'email': self.non_staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.url, {
            'name': 'New Item',
            'description': 'Description',
            'price': 15.0,
            'quantity': 30,
            'category': self.category.id,
            'is_with_prescription': False
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_staff_user_can_create_item(self):
        token = \
            self.client.post(self.login_url, data={'email': self.staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.post(self.url, {
            'name': 'New Item',
            'description': 'New Description',
            'price': 15.0,
            'quantity': 30,
            'category': self.category.id,
            'is_with_prescription': False
        })
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Item.objects.count(), 3)

    def test_staff_user_can_update_item(self):
        token = \
            self.client.post(self.login_url, data={'email': self.staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('item-detail', args=[self.item1.id])
        response = self.client.put(url, {
            'name': 'Updated Painkiller',
            'description': 'Updated description',
            'price': 20.0,
            'quantity': 150,
            'category': self.category.id,
            'is_with_prescription': False
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.name, 'Updated Painkiller')

    def test_staff_user_can_delete_item(self):
        token = \
            self.client.post(self.login_url, data={'email': self.staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('item-detail', args=[self.item1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(Item.objects.count(), 1)

    def test_non_staff_user_cannot_update_item(self):
        token = \
            self.client.post(self.login_url,
                             data={'email': self.non_staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('item-detail', args=[self.item1.id])
        response = self.client.put(url, {
            'name': 'Updated Painkiller',
            'description': 'Updated description',
            'price': 20.0,
            'quantity': 150,
            'category': self.category.id,
            'is_with_prescription': False
        })
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_non_staff_user_cannot_delete_item(self):
        token = \
            self.client.post(self.login_url,
                             data={'email': self.non_staff_user.email, 'password': self.password}).json()[
                'access_token']
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        url = reverse('item-detail', args=[self.item1.id])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class BusinessStatisticsIntegrationTests(APITestCase):

    def setUp(self):
        self.admin_user = User.objects.create_superuser(
            email='admin@example.com',
            password='adminpass',
            name='Admin'
        )
        self.client.force_authenticate(user=self.admin_user)

        # Setup test data
        self.category = Category.objects.create(name="Category1")
        item = Item.objects.create(
            name="Item1",
            category=self.category,
            price=100.00
        )
        Order.objects.create(item=item, total_price=1000.00, quantity=10, user=self.admin_user)

    def test_get_business_statistics(self):
        url = reverse('business-statistics')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIn('total_sales', data)
        self.assertIn('total_orders', data)
        self.assertIn('revenue_by_category', data)
        self.assertIn('average_order_value', data)
        self.assertIn('top_selling_products', data)

        self.assertEqual(data['total_sales'], '1000.00')
        self.assertEqual(data['total_orders'], 1)
        self.assertEqual(data['revenue_by_category'][f'{self.category.id}'], '1000.00')
        self.assertEqual(data['average_order_value'], '1000.00')
        self.assertEqual(len(data['top_selling_products']), 1)
        self.assertEqual(data['top_selling_products'][0]['name'], 'Item1')

    def test_no_orders(self):
        # Clear orders
        Order.objects.all().delete()

        url = reverse('business-statistics')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertEqual(data['total_sales'], '0.00')
        self.assertEqual(data['total_orders'], 0)
        self.assertEqual(data['revenue_by_category'], {})
        self.assertEqual(data['average_order_value'], '0.00')
        self.assertEqual(len(data['top_selling_products']), 0)

    def test_non_admin_access(self):
        self.client.logout()
        user = User.objects.create_user(email='user@example.com', password='userpass', name='User')
        self.client.force_authenticate(user=user)

        url = reverse('business-statistics')
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)


class ItemBuyIntegrationTests(APITestCase):

    def setUp(self):
        self.category = Category.objects.create(name="Test Category")
        self.item_with_stock = Item.objects.create(
            name="Item With Stock",
            category=self.category,
            price=Decimal('10.00'),
            quantity=100,
            is_with_prescription=False
        )
        self.item_with_prescription = Item.objects.create(
            name="Item With Prescription",
            category=self.category,
            price=Decimal('20.00'),
            quantity=50,
            is_with_prescription=True
        )
        self.user = Account.objects.create_user(
            email='user@example.com',
            name='Test User',
            password='password123'
        )
        self.anonymous_user_email = 'anonymous@example.com'
        self.anonymous_user = Account.objects.create_user(
            email=self.anonymous_user_email,
            name='Anonymous User',
            password='password123'
        )
        self.url = reverse('item-buy', kwargs={'pk': self.item_with_stock.pk})

    def test_buy_item_not_found(self):
        response = self.client.post(reverse('item-buy', kwargs={'pk': 999}), data={'quantity': 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], "Item can't be found!")

    def test_buy_item_with_prescription(self):
        response = self.client.post(reverse('item-buy', kwargs={'pk': self.item_with_prescription.pk}),
                                    data={'quantity': 1})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], "Item is with prescription and can't be bought online!")

    def test_buy_item_insufficient_quantity(self):
        response = self.client.post(self.url, data={'quantity': 101})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], "Not enough of the product. Currently available - 100!")

    def test_buy_item_success_authenticated_user(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.post(self.url, data={'quantity': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], "Bought 5 items for 50.0.")
        self.assertEqual(Item.objects.get(pk=self.item_with_stock.pk).quantity, 95)
        self.assertTrue(Order.objects.filter(item=self.item_with_stock, user=self.user).exists())

    def test_buy_item_success_anonymous_user(self):
        response = self.client.post(self.url, data={'quantity': 5})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['message'], "Bought 5 items for 50.0.")
        self.assertEqual(Item.objects.get(pk=self.item_with_stock.pk).quantity, 95)
        self.assertTrue(Order.objects.filter(item=self.item_with_stock, user=self.anonymous_user).exists())

    def test_buy_item_zero_quantity(self):
        response = self.client.post(self.url, data={'quantity': 0})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['message'], "Can't buy 0 products.")


class OrderListIntegrationTests(APITestCase):

    def setUp(self):
        # Create a user
        self.user = Account.objects.create_user(
            email='user@example.com',
            name='Test User',
            password='password123'
        )

        # Create another user
        self.other_user = Account.objects.create_user(
            email='otheruser@example.com',
            name='Other User',
            password='password123'
        )

        # Create a category
        self.category = Category.objects.create(name='Test Category')

        # Create items
        self.item1 = Item.objects.create(
            name='Test Item 1',
            category=self.category,
            price=10.00,
            quantity=100,
            is_with_prescription=False
        )
        self.item2 = Item.objects.create(
            name='Test Item 2',
            category=self.category,
            price=20.00,
            quantity=50,
            is_with_prescription=False
        )

        # Create orders for the user
        self.order1 = Order.objects.create(
            item=self.item1,
            user=self.user,
            total_price=100.00,
            quantity=10
        )
        self.order2 = Order.objects.create(
            item=self.item2,
            user=self.user,
            total_price=200.00,
            quantity=10
        )

        # Create an order for another user
        self.order3 = Order.objects.create(
            item=self.item1,
            user=self.other_user,
            total_price=50.00,
            quantity=5
        )

        self.url = reverse('order-history')

    def test_order_list_authenticated(self):
        # Test that an authenticated user can access the order list
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Ensure only the user's orders are returned
        orders = Order.objects.filter(user=self.user).order_by('-order_date')
        serializer = OrderSerializer(orders, many=True)
        self.assertEqual(response.data, serializer.data)

    def test_order_list_unauthenticated(self):
        # Test that an unauthenticated user cannot access the order list
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_order_list_quantity_parameter(self):
        # Test the quantity query parameter
        self.client.force_authenticate(user=self.user)

        # Test with quantity = 1
        response = self.client.get(self.url, {'quantity': 1})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

        # Test with quantity = 2
        response = self.client.get(self.url, {'quantity': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

        # Test with quantity = 0 (should return all orders)
        response = self.client.get(self.url, {'quantity': 0})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

    def test_order_list_ordering(self):
        # Test that orders are returned in descending order by order_date
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        # The most recent order should be the first in the list
        orders = Order.objects.filter(user=self.user).order_by('-order_date')
        serializer = OrderSerializer(orders, many=True)
        self.assertEqual(response.data, serializer.data)

    def test_order_list_other_user(self):
        # Test that a user only sees their own orders
        self.client.force_authenticate(user=self.other_user)
        response = self.client.get(self.url)

        orders = Order.objects.filter(user=self.other_user).order_by('-order_date')
        serializer = OrderSerializer(orders, many=True)
        self.assertEqual(response.data, serializer.data)
        self.assertEqual(len(response.data), 1)
