from django.urls import path

from chats.consumers import ChatConsumer, AdminChatConsumer

websocket_urlpatterns = [
    path("workspace/", ChatConsumer.as_asgi()),
    path("<str:conversation>/", AdminChatConsumer.as_asgi())
]