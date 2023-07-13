import json

from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.core.exceptions import ObjectDoesNotExist

from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from .tokens import password_reset_token

from .mail import  send_password_reset_mail

from .models import User



@api_view(['POST'])
def request_password_reset(request):
    body = json.loads(request.body)
    email = body["email"]
    try:
        user = User.objects.get(email=email)
        send_password_reset_mail(user)
    except ObjectDoesNotExist:
        pass
    return Response(status=status.HTTP_200_OK)

@api_view(['POST'])
def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None
        
    if user and password_reset_token.check_token(user, token):
        body = json.loads(request.body)
        password = body["password"]
        user.set_password(password)
        user.save()
        return Response("Password reset successfully", status=status.HTTP_200_OK)
    return Response("Invalid token", status=status.HTTP_400_BAD_REQUEST)