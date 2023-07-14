from django.urls import path

from chats.consumers import AnonymousChatConsumer, ChatConsumer, AdminChatConsumer

websocket_urlpatterns = [
    path("anonymous/", AnonymousChatConsumer.as_asgi()),
    path("workspace/", ChatConsumer.as_asgi()),
    path("<str:conversation>/", AdminChatConsumer.as_asgi())
]