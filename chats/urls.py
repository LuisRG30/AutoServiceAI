from django.urls import path
from . import views

from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

urlpatterns = [
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('register/', views.RegisterView.as_view(), name='auth_register'),
    path('user/', views.UserView.as_view(), name='user'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('register-chat/', views.RegisterChatView.as_view(), name='register-chat'),
    path('conversations/', views.ConversationsView.as_view(), name='conversations'),
    path('archived-conversations/', views.ArchivedConversationsView.as_view(), name='archived-conversations'),
    path('conversations/<int:pk>/', views.ConversationDetailView.as_view(), name='conversation'),
    path('assign-conversation/', views.assign_conversation, name='assign-conversation'),
    path('unassign-conversation/', views.unassign_conversation, name='unassign-conversation'),
    path('my-conversation/', views.MyConversationView.as_view(), name='my-conversation'),
    path('messages/', views.MessagesView.as_view({'get': 'list'}), name='messages'),
    path('mark-as-read/', views.mark_message_as_read, name='mark-as-read'),
    path('payments/', views.PaymentsView.as_view(), name='payments'),
    path('payments/<int:pk>/', views.PaymentDetailView.as_view(), name='payment'),
    path('documents/', views.DocumentsView.as_view(), name='documents'),
    path('create-payment-intent/', views.create_payment, name='create-payment-intent'),
    path('webhook/', views.webhook, name='stripe-webhook'),
    path('whatsapp-webhook/', views.whatsapp_webhook, name='whatsapp-webhook')

]