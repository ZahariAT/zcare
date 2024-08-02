from django.core import mail
from django.urls import reverse
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken

from core.tokens import get_tokens_for_user


class RegisterIntegrationTests(APITestCase):

    def setUp(self):
        self.user_model = get_user_model()
        self.url = reverse('register')
        self.valid_data = {
            'email': 'testuser@example.com',
            'name': 'Test User',
            'password': 'strongpassword123',
            'password2': 'strongpassword123',
        }

    def test_register_user_and_send_activation_email(self):
        response = self.client.post(self.url, data=self.valid_data)
        self.assertEqual(response.status_code, 201)

        # Check if user was created
        user = self.user_model.objects.get(email=self.valid_data['email'])
        self.assertFalse(user.is_active)

        # Check if an email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn('Activate Your Account', mail.outbox[0].subject)
        self.assertIn('Please click the activation link', mail.outbox[0].body)
        self.assertIn('http://', mail.outbox[0].body)
        self.assertIn(user.email, mail.outbox[0].to)

    def test_register_user_with_invalid_data(self):
        invalid_data = {
            'email': 'testuser@example.com',
            'name': 'Test User',
            'password': 'strongpassword123',
            'password2': 'wrongpassword123',
        }

        response = self.client.post(self.url, data=invalid_data)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(self.user_model.objects.filter(email=invalid_data['email']).exists())
        self.assertEqual(len(mail.outbox), 0)  # No email should be sent


class AccountIntegrationTests(APITestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(email='user@example.com', name='Test User',
                                                        password='password123')

    def test_create_user_via_api(self):
        payload = {
            'email': 'newuser@example.com',
            'name': 'New User',
            'password': 'password123',
            'password2': 'password123',
        }
        response = self.client.post(reverse('register'), payload)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], payload['email'])

    def test_login_user_via_api(self):
        payload = {
            'email': 'user@example.com',
            'password': 'password123',
        }
        response = self.client.post(reverse('login'), payload)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('access_token' in response.data)


class ActivateUserIntegrationTests(APITestCase):

    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(
            email='testuser@example.com',
            name='Test User',
            password='TestPass123'
        )
        self.user.is_active = False
        self.user.save()

        self.tokens = get_tokens_for_user(self.user)
        self.activate_url = reverse('activate-user', kwargs={'token': self.tokens['access']})

    def test_user_activation_success(self):
        response = self.client.get(self.activate_url)
        self.user.refresh_from_db()

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.is_active)
        self.assertEqual(response.data['message'], 'Account activated successfully!')

    def test_user_activation_invalid_token(self):
        invalid_activate_url = reverse('activate-user', kwargs={'token': 'invalid_token'})
        response = self.client.get(invalid_activate_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Activation link is invalid!')

    def test_user_activation_user_not_found(self):
        self.user.delete()  # Delete the user to simulate a not found scenario
        response = self.client.get(self.activate_url)

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Activation link is invalid!')


class LoginUserIntegrationTests(APITestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='testuser@example.com',
            name='Test User',
            password='TestPass123'
        )
        self.url = reverse('login')

    def test_login_success(self):
        response = self.client.post(self.url, {'email': 'testuser@example.com', 'password': 'TestPass123'})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access_token', response.data)
        self.assertIn('refresh_token', response.data)
        self.assertEqual(response.data['email'], 'testuser@example.com')

    def test_login_invalid_credentials(self):
        response = self.client.post(self.url, {'email': 'testuser@example.com', 'password': 'wrong_password'})

        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)


class LogoutUserIntegrationTests(APITestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='testuser@example.com',
            name='Test User',
            password='TestPass123'
        )
        self.valid_token = RefreshToken.for_user(self.user)
        self.invalid_token = 'invalid_token'
        self.url = reverse('logout')

    def test_logout_success(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(self.valid_token.access_token))
        response = self.client.post(self.url, {'refresh_token': str(self.valid_token)})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_logout_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Bearer ' + str(self.valid_token.access_token))
        response = self.client.post(self.url, {'refresh_token': self.invalid_token})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('bad_token', response.data[0].code)

    def test_logout_no_token(self):
        response = self.client.post(self.url, {})
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn('detail', response.data)
        self.assertEqual(str(response.data['detail']), 'Authentication credentials were not provided.')


class DeleteAccountIntegrationTests(APITestCase):

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='testuser@example.com',
            name='Test User',
            password='TestPass123'
        )
        self.url = reverse('delete-user')
        self.client.force_authenticate(user=self.user)

    def create_user(self, email, password):
        User = get_user_model()
        user = User.objects.create_user(
            email=email,
            name='Test User',
            password=password
        )
        return user

    def test_delete_account_success(self):
        # Ensure user exists before deletion
        self.assertTrue(get_user_model().objects.filter(email=self.user.email).exists())

        response = self.client.delete(self.url)

        # Ensure user no longer exists after deletion
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(get_user_model().objects.filter(email=self.user.email).exists())

    def test_delete_account_unauthenticated(self):
        # Log out the user to simulate an unauthenticated request
        self.client.force_authenticate(user=None)

        response = self.client.delete(self.url)

        # Ensure the request is denied
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
