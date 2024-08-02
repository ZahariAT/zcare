from rest_framework.test import APITestCase, APISimpleTestCase, APIRequestFactory
from django.urls import reverse, resolve
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework import status
from unittest.mock import patch, PropertyMock
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.exceptions import ValidationError, AuthenticationFailed

from core.models import Account
from core.tokens import *
from core.views import *
from core.serializers import RegisterAccountSerializer


class TokenTests(TestCase):
    def setUp(self):
        self.user_model = get_user_model()
        self.user = self.user_model.objects.create_user(email='user@example.com', password='password123',
                                                        name='Test User')

    def test_custom_refresh_token_contains_email(self):
        # Generate a token using the CustomRefreshToken
        refresh = CustomRefreshToken.for_user(self.user)

        # Check that the email is included in the token payload
        self.assertEqual(refresh["email"], self.user.email)

    def test_get_tokens_for_user(self):
        # Generate tokens for a user
        tokens = get_tokens_for_user(self.user)

        # Check that the tokens dictionary contains 'refresh' and 'access'
        self.assertIn('refresh', tokens)
        self.assertIn('access', tokens)

        # Decode the access token to check the email is included
        decoded_access_token = jwt.decode(tokens['access'], settings.SECRET_KEY, algorithms=["HS256"])
        self.assertEqual(decoded_access_token['email'], self.user.email)

    @patch('core.tokens.jwt.decode')  # Mock the JWT decode function
    def test_token_decoder_valid_token(self, mock_jwt_decode):
        # Mock the decoded data to simulate a valid token
        mock_jwt_decode.return_value = {'user_id': self.user.id}

        # Decode the token
        user_id = token_decoder('fake_token')

        # Assert that the correct user_id is returned
        self.assertEqual(user_id, self.user.id)

    @patch('core.tokens.jwt.decode')
    def test_token_decoder_expired_token(self, mock_jwt_decode):
        # Mock the decode function to raise an ExpiredSignatureError
        mock_jwt_decode.side_effect = jwt.ExpiredSignatureError

        # Decode the token
        user_id = token_decoder('fake_token')

        # Assert that None is returned for an expired token
        self.assertIsNone(user_id)

    @patch('core.tokens.jwt.decode')
    def test_token_decoder_invalid_token(self, mock_jwt_decode):
        # Mock the decode function to raise an InvalidTokenError
        mock_jwt_decode.side_effect = jwt.InvalidTokenError

        # Decode the token
        user_id = token_decoder('fake_token')

        # Assert that None is returned for an invalid token
        self.assertIsNone(user_id)


class RegisterAccountSerializerTests(APITestCase):

    def setUp(self):
        self.valid_data = {
            'email': 'testuser@example.com',
            'name': 'Test User',
            'password': 'strongpassword123',
            'password2': 'strongpassword123',
        }

        self.invalid_data_mismatched_passwords = {
            'email': 'testuser@example.com',
            'name': 'Test User',
            'password': 'strongpassword123',
            'password2': 'wrongpassword123',
        }

    def test_serializer_valid_data(self):
        serializer = RegisterAccountSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        self.assertEqual(serializer.validated_data['email'], self.valid_data['email'])

    def test_serializer_invalid_mismatched_passwords(self):
        serializer = RegisterAccountSerializer(data=self.invalid_data_mismatched_passwords)
        self.assertFalse(serializer.is_valid())
        self.assertIn('password', serializer.errors)

    def test_serializer_create_user(self):
        serializer = RegisterAccountSerializer(data=self.valid_data)
        self.assertTrue(serializer.is_valid())
        user = serializer.save()
        self.assertEqual(user.email, self.valid_data['email'])
        self.assertFalse(user.is_active)
        self.assertTrue(user.check_password(self.valid_data['password']))


class AccountManagerTests(APITestCase):
    def setUp(self):
        self.user_model = get_user_model()

    def test_create_user(self):
        user = self.user_model.objects.create_user(email='user@example.com', name='Test User', password='password123')
        self.assertEqual(user.email, 'user@example.com')
        self.assertEqual(user.name, 'Test User')
        self.assertTrue(user.check_password('password123'))
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_no_email(self):
        with self.assertRaises(ValueError):
            self.user_model.objects.create_user(email='', name='Test User', password='password123')

    def test_create_user_no_name(self):
        with self.assertRaises(ValueError):
            self.user_model.objects.create_user(email='user@example.com', name='', password='password123')

    def test_create_pharmacist(self):
        user = self.user_model.objects.create_pharmacist(email='pharmacist@example.com', name='Pharmacist User',
                                                         password='password123')
        self.assertEqual(user.email, 'pharmacist@example.com')
        self.assertEqual(user.name, 'Pharmacist User')
        self.assertTrue(user.check_password('password123'))
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_superuser(self):
        user = self.user_model.objects.create_superuser(email='admin@example.com', name='Admin User',
                                                        password='password123')
        self.assertEqual(user.email, 'admin@example.com')
        self.assertEqual(user.name, 'Admin User')
        self.assertTrue(user.check_password('password123'))
        self.assertTrue(user.is_active)
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)


class RegisterUserViewTests(APITestCase):

    def setUp(self):
        self.user_model = get_user_model()
        self.url = reverse('register')
        self.valid_data = {
            'email': 'testuser@example.com',
            'name': 'Test User',
            'password': 'strongpassword123',
            'password2': 'strongpassword123',
        }

    @patch('core.views.get_tokens_for_user')
    @patch('core.views.send_mail')
    def test_post_valid_data(self, mock_send_mail, mock_get_tokens_for_user):
        mock_get_tokens_for_user.return_value = {'access': 'mocked_token'}

        response = self.client.post(self.url, data=self.valid_data)

        self.assertEqual(response.status_code, 201)
        self.assertTrue(self.user_model.objects.filter(email=self.valid_data['email']).exists())

        mock_send_mail.assert_called_once()
        mock_get_tokens_for_user.assert_called_once()
        email_body = mock_send_mail.call_args[0][1]
        expected_host = response.wsgi_request.get_host()
        expected_link = f'http://{expected_host}/api/activate/mocked_token'

        self.assertIn(expected_link, email_body)

    def test_post_invalid_data(self):
        invalid_data = {
            'email': 'testuser@example.com',
            'name': 'Test User',
            'password': 'strongpassword123',
            'password2': 'wrongpassword123',
        }

        response = self.client.post(self.url, data=invalid_data)
        self.assertEqual(response.status_code, 400)
        self.assertIn('password', response.data)
        self.assertFalse(self.user_model.objects.filter(email=invalid_data['email']).exists())


class ActivateUserViewTests(TestCase):

    def setUp(self):
        self.factory = APIRequestFactory()
        self.user = Account.objects.create_user(
            email='testuser@example.com',
            name='Test User',
            password='TestPass123'
        )
        self.user.is_active = False
        self.user.save()

    @patch('core.views.token_decoder')
    def test_activate_user_successfully(self, mock_token_decoder):
        mock_token_decoder.return_value = self.user.id
        request = self.factory.get(reverse('activate-user', kwargs={'token': 'dummy_token'}))

        response = ActivateUserView.as_view()(request, token='dummy_token')

        self.user.refresh_from_db()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(self.user.is_active)
        self.assertEqual(response.data['message'], 'Account activated successfully!')

    @patch('core.views.token_decoder')
    def test_activate_user_invalid_token(self, mock_token_decoder):
        mock_token_decoder.return_value = None
        request = self.factory.get(reverse('activate-user', kwargs={'token': 'invalid_token'}))

        response = ActivateUserView.as_view()(request, token='invalid_token')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Activation link is invalid!')

    @patch('core.views.token_decoder')
    def test_activate_user_user_not_found(self, mock_token_decoder):
        mock_token_decoder.return_value = 999  # Non-existent user ID
        request = self.factory.get(reverse('activate-user', kwargs={'token': 'dummy_token'}))

        response = ActivateUserView.as_view()(request, token='dummy_token')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['error'], 'Activation link is invalid!')


class LoginAccountSerializerTests(TestCase):

    def setUp(self):
        self.user = self.create_user(email='testuser@example.com', password='TestPass123')

    def create_user(self, email, password):
        User = get_user_model()
        user = User.objects.create_user(
            email=email,
            name='Test User',
            password=password
        )
        return user

    def test_valid_login(self):
        data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123'
        }
        serializer = LoginAccountSerializer(data=data, context={'request': None})
        self.assertTrue(serializer.is_valid())
        response_data = serializer.validated_data
        self.assertEqual(response_data['email'], self.user.email)
        self.assertEqual(response_data['full_name'], self.user.name)
        self.assertTrue(response_data['access_token'])
        self.assertTrue(response_data['refresh_token'])

    def test_invalid_credentials(self):
        data = {
            'email': 'testuser@example.com',
            'password': 'WrongPassword'
        }
        serializer = LoginAccountSerializer(data=data, context={'request': None})
        with self.assertRaises(AuthenticationFailed):
            serializer.is_valid(raise_exception=True)

    def test_inactive_user(self):
        self.user.is_active = False
        self.user.save()
        data = {
            'email': 'testuser@example.com',
            'password': 'TestPass123'
        }
        serializer = LoginAccountSerializer(data=data, context={'request': None})
        with self.assertRaises(AuthenticationFailed):
            serializer.is_valid(raise_exception=True)


class LogoutUserSerializerTests(TestCase):

    def setUp(self):
        self.valid_token = str(RefreshToken.for_user(self.create_user()))
        self.invalid_token = 'invalid_token'

    def test_valid_token(self):
        serializer = LogoutUserSerializer(data={'refresh_token': self.valid_token})
        self.assertTrue(serializer.is_valid())
        try:
            serializer.save()
        except ValidationError as e:
            self.fail(f"Serializer raised ValidationError: {e}")

    def test_invalid_token(self):
        serializer = LogoutUserSerializer(data={'refresh_token': self.invalid_token})
        serializer.is_valid()
        try:
            serializer.save()
        except ValidationError as e:
            pass

    def create_user(self):
        # Create a user for generating a valid refresh token
        User = get_user_model()
        user = User.objects.create_user(
            email='testuser@example.com',
            name='Test User',
            password='TestPass123'
        )
        return user
