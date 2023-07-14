from urllib.parse import parse_qsl
from asgiref.sync import async_to_sync

from django.core.cache import cache

from .models import Integration, Conversation, Message, Document, Payment
from users.models import User
from .serializers import MessageSerializer
from .mail import send_message_notification, send_document_upload_notification, send_document_requested_notification, send_payment_requested_notification, send_new_conversation_notification_admins

from channels.generic.websocket import JsonWebsocketConsumer



class ChatConsumer(JsonWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.conversation = None
    def connect(self):
        try:
            query_string = self.scope["query_string"].decode("utf-8")
            query_params = dict(parse_qsl(query_string))
            ticket_uuid = query_params["ticket_uuid"]
            suspected_user = cache.get(ticket_uuid)
            if cache.delete(ticket_uuid):
                self.scope["user"] = suspected_user
                self.conversation = suspected_user.email.replace("@", ".")
            else:
                raise ValueError("Invalid ticket!")
        except:
            self.close()
            raise ValueError("Error getting ticket")
        self.accept()
        

        try:
            integration = Integration.objects.get(channel='integrated')
            conversation, created = Conversation.objects.get_or_create(integration=integration, name=self.conversation)
            if created:
                conversation.user = User.objects.first()
                conversation.save()
                send_new_conversation_notification_admins(conversation)
        except Exception:
            pass
        
        async_to_sync(self.channel_layer.group_add)(
            self.conversation, self.channel_name
        )
        messages = conversation.messages.all().order_by("-created_at")[0:50]
        self.send_json({
            "type": "last_messages",
            "messages": MessageSerializer(messages, many=True).data
        })

    def disconnect(self, code):
        return super().disconnect(code)

    def receive_json(self, content, **kwargs):
        message_type = content["type"]
        if message_type == "typing":
            async_to_sync(self.channel_layer.group_send)(
                self.conversation,
                {
                    "type": "typing_echo",
                    "sender": self.scope["user"].email,
                    "typing": content["typing"],    
                },
            )

        if message_type == "chat_message":
            conversation = Conversation.objects.get(name=self.conversation)
            last_message_in_conversation = conversation.messages.all().order_by("-created_at").first()
            message = Message.objects.create(
                conversation=conversation,
                from_user=self.scope["user"],
                message=content["message"],
            )
            if last_message_in_conversation:
                if (last_message_in_conversation.created_at - message.created_at).total_seconds() > 3600:
                    send_message_notification(message)
            else:
                send_message_notification(message)
            docs = content["documents"]
            if docs:
                for index, document_id in enumerate(docs):
                    try:
                        document = Document.objects.get(id=document_id, conversation=conversation, staging=True)
                        if index == 0:
                            document.message = message
                        else:
                            message = Message.objects.create(
                                conversation=conversation,
                                from_user=self.scope["user"],
                                message="",
                            )
                            document.message = message
                        document.staging = False
                        document.save()
                        send_document_upload_notification(document)
                    except:
                        pass
                    async_to_sync(self.channel_layer.group_send)(
                        self.conversation,
                        {
                            "type": "chat_message_echo",
                            "sender": self.scope["user"].email,
                            "message": MessageSerializer(message).data,
                        },
                    )
            else:
                async_to_sync(self.channel_layer.group_send)(
                    self.conversation,
                    {
                        "type": "chat_message_echo",
                        "sender": self.scope["user"].email,
                        "message": MessageSerializer(message).data,
                    },
                )
        return super().receive_json(content, **kwargs)

    def typing_echo(self, event):
        self.send_json(event)

    def chat_message_echo(self, event):
        self.send_json(event)

class AdminChatConsumer(JsonWebsocketConsumer):

    def __init__(self, *args, **kwargs):
        super().__init__(args, kwargs)
        self.conversation = None

    def connect(self):
        try:
            self.conversation = self.scope["url_route"]["kwargs"]["conversation"].replace("@", ".")
        except KeyError:
            raise ValueError("Conversation not found!")

        try:
            query_string = self.scope["query_string"].decode("utf-8")
            query_params = dict(parse_qsl(query_string))
            ticket_uuid = query_params["ticket_uuid"]
            suspected_user = cache.get(ticket_uuid)
            if cache.delete(ticket_uuid) and suspected_user.profile.admin:
                self.scope["user"] = suspected_user
            else:
                raise ValueError("Invalid ticket!")
        except:
            self.close()
            raise ValueError("Error getting ticket")

        try:
            conversation = Conversation.objects.get(name=self.conversation)
        except Conversation.DoesNotExist:
            self.close()
            raise ValueError("Conversation not found!")

        self.accept()
        
        async_to_sync(self.channel_layer.group_add)(
            self.conversation, self.channel_name
        )
        messages = conversation.messages.all().order_by("-created_at")[0:50]
        self.send_json({
            "type": "last_messages",
            "messages": MessageSerializer(messages, many=True).data
        })

    def disconnect(self, code):
        return super().disconnect(code)

    def receive_json(self, content, **kwargs):
        message_type = content["type"]
        if message_type == "typing":
            async_to_sync(self.channel_layer.group_send)(
                self.conversation,
                {
                    "type": "typing_echo",
                    "sender": self.scope["user"].email,
                    "typing": content["typing"],    
                },
            )

        if message_type == "chat_message":
            conversation = Conversation.objects.get(name=self.conversation)
            message = Message.objects.create(
                conversation=conversation,
                from_user=self.scope["user"],
                message=content["message"],
            )
            send_message_notification(message)
            docs = content["documents"]
            if docs:
                for index, document_id in enumerate(docs):
                    try:
                        document = Document.objects.get(id=document_id, conversation=conversation, staging=True)
                        if index == 0:
                            document.message = message
                        else:
                            message = Message.objects.create(
                                conversation=conversation,
                                from_user=self.scope["user"],
                                message="",
                            )
                            document.message = message
                        document.staging = False
                        document.save()
                        send_document_upload_notification(document)
                    except:
                        pass
                    async_to_sync(self.channel_layer.group_send)(
                        self.conversation,
                        {
                            "type": "chat_message_echo",
                            "sender": self.scope["user"].email,
                            "message": MessageSerializer(message).data,
                        },
                    )
            else:
                async_to_sync(self.channel_layer.group_send)(
                    self.conversation,
                    {
                        "type": "chat_message_echo",
                        "sender": self.scope["user"].email,
                        "message": MessageSerializer(message).data,
                    },
                )
        if message_type == "request_payment":
            conversation = Conversation.objects.get(name=self.conversation)
            message = Message.objects.create(
                conversation=conversation,
                from_user=self.scope["user"],
                message=None
            )
            payment = Payment.objects.create(
                conversation=conversation,
                message=message,
                description=content["description"],
                amount_cents=content["amount"],
            )
            send_payment_requested_notification(payment)
            async_to_sync(self.channel_layer.group_send)(
                self.conversation,
                {
                    "type": "chat_message_echo",
                    "sender": self.scope["user"].email,
                    "message": MessageSerializer(message).data
                }
            )

        if message_type == "request_document":
            conversation = Conversation.objects.get(name=self.conversation)
            message = Message.objects.create(
                conversation=conversation,
                from_user=self.scope["user"],
                message=None
            )
            document = Document.objects.create(
                conversation=conversation,
                message=message,
                requirement=content["document"]
            )
            send_document_requested_notification(document)
            async_to_sync(self.channel_layer.group_send)(
                self.conversation,
                {
                    "type": "chat_message_echo",
                    "sender": self.scope["user"].email,
                    "message": MessageSerializer(message).data
                }
            )
        
        return super().receive_json(content, **kwargs)

    def chat_message_echo(self, event):
        self.send_json(event)