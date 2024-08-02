from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated
from django.core.mail import send_mail
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django.http import Http404

from .models import Account
from .serializers import RegisterAccountSerializer, LoginAccountSerializer, LogoutUserSerializer
from .tokens import get_tokens_for_user, token_decoder

User = get_user_model()


class RegisterUserView(APIView):
    def post(self, request):
        serializer = RegisterAccountSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            token = get_tokens_for_user(user)

            current_site = request.get_host()
            activation_link = f'http://{current_site}/api/activate/{token["access"]}'

            send_mail(
                'Activate Your Account',
                f'Please click the activation link to activate your account: {activation_link}',
                settings.EMAIL_HOST_USER,
                [user.email],
                fail_silently=False,
            )

            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ActivateUserView(APIView):
    def get(self, request, token):
        user_id = token_decoder(token)

        try:
            user = get_object_or_404(Account, pk=user_id)
            user.is_active = True
            user.save()
            return Response({'message': 'Account activated successfully!'}, status=status.HTTP_200_OK)
        except Http404:
            return Response({'error': 'Activation link is invalid!'}, status=status.HTTP_400_BAD_REQUEST)


class LoginUserView(APIView):
    def post(self, request):
        serializer = LoginAccountSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LogoutUserView(APIView):
    serializer_class = LogoutUserSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeleteAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, *args, **kwargs):
        user = self.request.user
        user.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)
