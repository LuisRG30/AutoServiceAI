import string
import random

from urllib.parse import parse_qsl
from asgiref.sync import async_to_sync

from django.core.cache import cache
from django.conf import settings

from .models import Integration, Conversation, Message, Document, Payment, Profile
from users.models import User
from .serializers import MessageSerializer
from .mail import send_message_notification, send_document_upload_notification, send_document_requested_notification, send_payment_requested_notification, send_new_conversation_notification_admins, send_conversation_autopilot_deactivated

from .my_gpt import get_my_ai_response

from channels.generic.websocket import JsonWebsocketConsumer

class AnonymousChatConsumer(JsonWebsocketConsumer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conversation = None

    def connect(self):
        query_string = self.scope["query_string"].decode("utf-8")
        query_params = dict(parse_qsl(query_string))
        web_token = query_params["web_token"]
        try:
            conversation_name = query_params["conversation_name"]
        except Exception:
            conversation_name = None
        try: 
            integration = Integration.objects.get(channel="web", web_token=web_token)
        except:
            self.close()
            raise ValueError("Invalid Web Integration")
        try:
            if conversation_name:
                conversation = Conversation.objects.get(name=conversation_name, user=None)
            else:
                new_name = ''.join(random.choices(string.ascii_uppercase + string.digits, k=16))
                conversation = Conversation.objects.create(name=new_name, integration=integration)
        except Conversation.DoesNotExist:
            conversation = Conversation.objects.create(name=conversation_name, integration=integration)
        self.conversation = conversation.name

        self.accept()

        async_to_sync(self.channel_layer.group_add)(
            self.conversation, self.channel_name
        )
        messages = conversation.messages.all().order_by("-created_at")[0:50]
        self.send_json({
            "type": "last_messages",
            "conversation_name": self.conversation,
            "messages": MessageSerializer(messages, many=True).data
        })

    def disconnect(self, code):
        return super().disconnect(code)
    
    def receive_json(self, content, **kwargs):
        message_type = content["type"]
        if message_type == "chat_message":
            conversation = Conversation.objects.get(name=self.conversation)
            last_message_in_conversation = conversation.messages.all().order_by("-created_at").first()
            anonymous_user = User.objects.get(profile__Anonymous=True)
            message = Message.objects.create(
                conversation=conversation,
                from_user=anonymous_user,
                message=content["message"],
            )
            if last_message_in_conversation:
                if (last_message_in_conversation.created_at - message.created_at).total_seconds() > 3600:
                    send_message_notification(message)
            else:
                send_message_notification(message)
 
            async_to_sync(self.channel_layer.group_send)(
                self.conversation,
                {
                    "type": "chat_message_echo",
                    "sender": self.scope["user"].email,
                    "message": MessageSerializer(message).data,
                },
            )
        return super().receive_json(content, **kwargs)
    
    def chat_message_echo(self, event):
        self.send_json(event)

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
                conversation.user = suspected_user
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
            if conversation.autopilot:
                past_messages = Message.objects.filter(conversation=conversation).order_by('-created_at')[:settings.AI_CONTEXT_SIZE]
                past_messages = past_messages[::-1]
                past_messages = MessageSerializer(past_messages, many=True).data

                try:
                    ai_response = get_my_ai_response(past_messages)
                    
                    ai_user = Profile.objects.get(AI=True).user
                    ai_message = Message.objects.create(
                                        conversation=conversation,
                                        from_user=ai_user,
                                        message=ai_response,
                                        read=False
                                    )
                    
                    try:
                        async_to_sync(self.channel_layer.group_send)(
                            conversation.name,
                            {
                                'type': 'chat_message_echo',
                                'sender': ai_user,
                                'message': MessageSerializer(ai_message).data
                            }
                        )
                    except Exception as e:
                        print(e)
                    
                except Exception as e:
                    conversation.autopilot = False
                    conversation.save()
                    send_conversation_autopilot_deactivated(conversation)

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