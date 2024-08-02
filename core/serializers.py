from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken, TokenError

from .models import Account
from .tokens import get_tokens_for_user


class RegisterAccountSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(max_length=255, required=True)
    name = serializers.CharField(max_length=255, write_only=True)
    password = serializers.CharField(max_length=255, write_only=True)
    password2 = serializers.CharField(max_length=255, write_only=True, required=True)

    class Meta:
        model = Account
        fields = ("email", "name", "password", "password2")

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        user = Account.objects.create_user(
            email=validated_data["email"], password=validated_data["password"],
            name=validated_data["name"]
        )
        user.is_active = False
        user.save()
        return user


class LoginAccountSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(max_length=255, write_only=True)
    name = serializers.CharField(max_length=255, read_only=True)
    access_token = serializers.CharField(max_length=255, read_only=True)
    refresh_token = serializers.CharField(max_length=255, read_only=True)

    class Meta:
        model = Account
        fields = ['email', 'password', 'name', 'access_token', 'refresh_token']

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        request = self.context.get('request')
        user = authenticate(request, email=email, password=password)
        if not user:
            raise AuthenticationFailed("invalid credential try again")
        if not user.is_active:
            raise AuthenticationFailed("Email is not active")
        tokens = get_tokens_for_user(user)
        return {
            'email': user.email,
            'full_name': user.name,
            "access_token": str(tokens.get('access')),
            "refresh_token": str(tokens.get('refresh'))
        }


class LogoutUserSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()

    default_error_messages = {
        'bad_token': ('Token is expired or invalid')
    }

    def validate(self, attrs):
        self.refresh_token = attrs.get('refresh_token')

        return attrs

    def save(self, **kwargs):
        try:
            token = RefreshToken(self.refresh_token)
            token.blacklist()
        except TokenError:
            return self.fail('bad_token')
