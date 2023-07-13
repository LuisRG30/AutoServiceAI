from django.urls import path
from . import views

urlpatterns = [
    path('request-password-reset/', views.request_password_reset, name='request-password-reset'),
    path('password-reset/<uidb64>/<token>/', views.reset_password, name='password-reset'),
]
