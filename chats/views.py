import stripe
import json
import datetime

from asgiref.sync import async_to_sync

from channels.layers import get_channel_layer

from uuid import uuid4
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required


from django.conf import settings
from django.shortcuts import render
from django.core.cache import cache
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from django.http import HttpResponse
from rest_framework.mixins import ListModelMixin
from rest_framework.decorators import api_view
from rest_framework import status, generics
from rest_framework.permissions import IsAuthenticated, AllowAny

from .models import Conversation, Message, Document, Payment, PaymentIntent, Profile, Integration
from .serializers import RegisterSerializer, UserSerializer, ProfileSerializer, ConversationSerializer, MessageSerializer, DocumentSerializer, PaymentSerializer
from .permissions import IsAdmin, IsAdminOrReadAuthenticated
from .paginaters import MessagePagination
from .my_gpt import get_my_ai_response
from .mail import send_payment_success_mail, send_payment_notification_admins, send_document_upload_notification, send_conversation_assignment_notification, send_conversation_unassignment_notification, send_conversation_archive_change_notification, send_conversation_autopilot_deactivated

stripe.api_key = settings.STRIPE_SECRET_KEY
endpoint_secret = settings.STRIPE_ENDPOINT_SECRET

User = get_user_model()

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

class UserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        data = UserSerializer(user).data
        return Response(data, status=status.HTTP_200_OK)

class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        profile = Profile.objects.get(user=user)
        data = ProfileSerializer(profile).data
        return Response(data, status=status.HTTP_200_OK)
    
class RegisterChatView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        ticket_uuid = str(uuid4())
        cache.set(ticket_uuid, request.user, timeout=60)
        return Response({'ticket_uuid': ticket_uuid})

class ConversationsView(ListAPIView):
    permission_classes = [IsAdmin]
    serializer_class = ConversationSerializer
    queryset = Conversation.objects.filter(archived=False)

class ArchivedConversationsView(APIView):
    permission_classes = [IsAdmin]
    
    def get(self, request):
        conversations = Conversation.objects.filter(archived=True)
        data = ConversationSerializer(conversations, many=True).data
        return Response(data, status=status.HTTP_200_OK)
    
    def post(self, request):
        conversation_id = request.data.get('id', None)
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)
            conversation.archived = conversation.archived == False
            conversation.save()
            send_conversation_archive_change_notification(conversation)
            return Response({'success': True}, status=status.HTTP_200_OK)
        return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)

class ConversationDetailView(APIView):
    permission_classes = [IsAdminOrReadAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            conversation = Conversation.objects.get(id=pk)
        except Conversation.DoesNotExist:
            return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)
        return Response(ConversationSerializer(conversation).data, status=status.HTTP_200_OK)
    
    def put(self, request, pk, *args, **kwargs):
        try:
            conversation = Conversation.objects.get(id=pk)
        except Conversation.DoesNotExist:
            return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)
        serializer = ConversationSerializer(conversation, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk, *args, **kwargs):
        try:
            conversation = Conversation.objects.get(id=pk)
        except Conversation.DoesNotExist:
            return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)
        conversation.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)


class MyConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        name = user.email.replace('@', '.')
        try:
            conversation = Conversation.objects.get(name=name, user=user)
        except Conversation.DoesNotExist:
            conversation = Conversation.objects.create(name=name, user=user)
        return Response(ConversationSerializer(conversation).data, status=status.HTTP_200_OK)

class MessagesView(ListModelMixin, GenericViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = MessageSerializer
    pagination_class = MessagePagination

    def get_queryset(self):
        conversation_id = self.request.query_params.get('conversation')
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                return Message.objects.none()
            user = self.request.user
            if conversation.user == user or user.profile.admin:
                return Message.objects.filter(conversation=conversation).order_by('-created_at')
        return Message.objects.none()


class DocumentsView(APIView):
    permission_classes = [IsAuthenticated]
    lookup_url_kwargs = ['conversation']

    def get(self, request):
        conversation_id = request.query_params.get(self.lookup_url_kwargs[0], None)
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)
            user = request.user
            if conversation.user == user or user.profile.admin:
                documents = Document.objects.filter(conversation=conversation)
                return Response(DocumentSerializer(documents, many=True).data, status=status.HTTP_200_OK)
        else:
            if request.user.profile.admin:
                documents = Document.objects.all()
                return Response(DocumentSerializer(documents, many=True).data, status=status.HTTP_200_OK)
            else:
                return Response({'success': False}, status=status.HTTP_401_UNAUTHORIZED)
                
    def post(self, request):
        data = request.data
        file = request.FILES.get('file')
        try:
            conversation = Conversation.objects.get(id=data['conversation'])
        except Conversation.DoesNotExist:
            return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)
        staging = data.get('staging')
        if conversation.user != request.user and not request.user.profile.admin:
            return Response({'success': False}, status=status.HTTP_401_UNAUTHORIZED)
        if not staging:
            staging = False
        else:
            staging = True

        message = Message.objects.create(
            conversation=conversation,
            from_user=request.user,
            read=True
        )
        document = Document.objects.create(
            name=file.name,
            conversation=conversation,
            file=file,
            staging=staging,
            message=message
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            conversation.name,
            {
                'type': 'chat_message_echo',
                'sender': message.from_user.email,
                'message': MessageSerializer(message).data
            }
        )
        send_document_upload_notification(document)
        return Response(DocumentSerializer(document).data, status=status.HTTP_201_CREATED)

class PaymentsView(APIView):
    permission_classes = [IsAdminOrReadAuthenticated]
    lookup_url_kwargs = ['conversation']

    def get(self, request):
        conversation_id = request.query_params.get(self.lookup_url_kwargs[0], None)
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                return Response({'error': 'Conversation not found'}, status=status.HTTP_400_BAD_REQUEST)
            if conversation.user != request.user and not request.user.profile.admin:
                return Response({'error': 'Not authorized'}, status=status.HTTP_401_UNAUTHORIZED)
            payments = Payment.objects.filter(conversation=conversation)
            return Response(PaymentSerializer(payments, many=True).data)
        else:
            if request.user.profile.admin:
                payments = Payment.objects.all()
                return Response(PaymentSerializer(payments, many=True).data)
            else:
                return Response({'error': 'Not authorized'}, status=status.HTTP_401_UNAUTHORIZED)

    def post(self, request):
        data = request.data
        try:
            conversation = Conversation.objects.get(id=data['conversation'])
        except Conversation.DoesNotExist:
            return Response({'error': 'Conversation not found'}, status=status.HTTP_400_BAD_REQUEST)
        try:
            payment = Payment.objects.create(
                conversation=conversation,
                amount_cents=data['amount'],
                description=data['description']
            )
        except KeyError:
            return Response({'error': 'Missing data'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(PaymentSerializer(payment).data, status=status.HTTP_201_CREATED)

class PaymentDetailView(APIView):
    permission_classes = [IsAdminOrReadAuthenticated]

    def get(self, request, pk):
        try:
            payment = Payment.objects.get(id=pk)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_400_BAD_REQUEST)
        if payment.conversation.user != request.user and not request.user.profile.admin:
            return Response({'error': 'Not authorized'}, status=status.HTTP_401_UNAUTHORIZED)
        return Response(PaymentSerializer(payment).data)

    def put(self, request, pk):
        data = request.data
        try:
            payment = Payment.objects.get(id=pk)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_400_BAD_REQUEST)
        if 'amount' in data:
            payment.amount_cents = data['amount']
        if 'description' in data:
            payment.description = data['description']
        payment.save()
        return Response(PaymentSerializer(payment).data)

    def delete(self, request, pk):
        try:
            payment = Payment.objects.get(id=pk)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_400_BAD_REQUEST)
        payment.delete()
        return Response({'success': True}, status=status.HTTP_200_OK)
    
@api_view(['POST'])
def assign_conversation(request):
    try:
        data = request.data
        conversation_id = data['conversation']
        conversation = Conversation.objects.get(id=conversation_id)
    except KeyError:
        return Response({'error': 'Missing data'}, status=status.HTTP_400_BAD_REQUEST)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.profile.admin:
        return Response({'error': 'Not authorized'}, status=status.HTTP_401_UNAUTHORIZED)
    conversation.assigned_to = request.user
    conversation.save()
    send_conversation_assignment_notification(conversation)
    return Response({'success': True}, status=status.HTTP_200_OK)

@api_view(['POST'])
def unassign_conversation(request):
    try:
        data = request.data
        conversation_id = data['conversation']
        conversation = Conversation.objects.get(id=conversation_id)
    except KeyError:
        return Response({'error': 'Missing data'}, status=status.HTTP_400_BAD_REQUEST)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_400_BAD_REQUEST)
    if not request.user.profile.admin:
        return Response({'error': 'Not authorized'}, status=status.HTTP_401_UNAUTHORIZED)
    if conversation.assigned_to != request.user:
        return Response({'error': 'Not authorized'}, status=status.HTTP_401_UNAUTHORIZED)
    conversation.assigned_to = None
    conversation.save()
    send_conversation_unassignment_notification(conversation)
    return Response({'success': True}, status=status.HTTP_200_OK)
        
@api_view(['POST'])
def mark_message_as_read(request):
    try:
        data = request.data
        message_id = data['message']
        message = Message.objects.get(id=message_id)
    except KeyError:
        return Response({'error': 'Missing data'}, status=status.HTTP_400_BAD_REQUEST)
    except Message.DoesNotExist:
        return Response({'error': 'Message not found'}, status=status.HTTP_400_BAD_REQUEST)
    if message.conversation.user != request.user and not request.user.profile.admin:
        return Response({'error': 'Not authorized'}, status=status.HTTP_401_UNAUTHORIZED)
    message.read = True
    message.save()
    return Response({'success': True}, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_payment(request):
    try:
        user = request.user
        conversation = Conversation.objects.get(user=user)
    except User.DoesNotExist:
        return Response({'error': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
    except Conversation.DoesNotExist:
        return Response({'error': 'Conversation not found'}, status=status.HTTP_400_BAD_REQUEST)
    try:
        data = json.loads(request.body)
        payment_id = data['payment_id']
        try:
            payment = Payment.objects.get(id=payment_id)
        except Payment.DoesNotExist:
            return Response({'error': 'Payment not found'}, status=status.HTTP_400_BAD_REQUEST)
        intent = stripe.PaymentIntent.create(
            amount=payment.amount_cents,
            currency='mxn',
            automatic_payment_methods={
                'enabled': True,
            }
        )
        PaymentIntent.objects.create(
            payment=payment,
            payment_intent_id=intent['id'],
        )
        return Response({'client_secret': intent['client_secret']})
    except Exception as e:
        return Response({'error': str(e)})

@csrf_exempt
@api_view(['POST']) 
def webhook(request):
    try:
        payload = request.body
        request_data = json.loads(payload)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    if endpoint_secret:
        signature = request.headers.get('stripe-signature')
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=endpoint_secret
            )
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except stripe.error.SignatureVerificationError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        if event['type'] == 'payment_intent.succeeded':
            payment_intent = event['data']['object']
            try:
                payment_intent_object = PaymentIntent.objects.get(payment_intent_id=payment_intent['id'])
                payment = payment_intent_object.payment
                payment.paid = True
                payment.date_paid = datetime.datetime.utcnow()
                payment.save()
                send_payment_success_mail(payment)
                send_payment_notification_admins(payment)
            except PaymentIntent.DoesNotExist:
                return Response({'error': 'Payment intent not found'}, status=status.HTTP_400_BAD_REQUEST)
        elif event['type'] == 'payment_intent.created':
            payment_method = event['data']['object']
        else:
            #Unexpected event type
            return Response({'error': 'Unexpected event type'}, status=status.HTTP_400_BAD_REQUEST)

    return Response({'success': True}, status=status.HTTP_200_OK)


@api_view(['POST', 'GET'])
def whatsapp_webhook(request):
    if request.method == 'GET':
        verification = request.GET.get('hub.challenge')
        return HttpResponse(verification, status=status.HTTP_200_OK, content_type='text/plain')
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        entries = data['entry']
        for entry in entries:
            changes = entry['changes']
            for change in changes:
                messages = change['value']['messages']
                for message in messages:
                    phone_number = message['from']
                    whatsapp_integration = Integration.objects.get_or_create(channel='whatsapp')

                    try:
                        sender_user = User.objects.get(phone=phone_number)
                    except User.DoesNotExist:
                        sender_user = User.objects.create(phone=phone_number)
                        
                    conversation, created = Conversation.objects.get_or_create(name=phone_number,
                                                                                integration=whatsapp_integration,
                                                                                user=sender_user)
                                                                                
                    if conversation.integration.channel != 'whatsapp':
                        return Response({'success': False}, status=status.HTTP_400_BAD_REQUEST)
                    
                    new_message = Message.objects.create(
                                        conversation=conversation,
                                        from_user=conversation.user,
                                        message=message['text']['body'],
                                        read=False
                                    )
                    
                    try:
                        channel_layer = get_channel_layer()
                        async_to_sync(channel_layer.group_send)(
                            conversation.name,
                            {
                                'type': 'chat_message_echo',
                                'sender': new_message.from_user.phone,
                                'message': MessageSerializer(new_message).data
                            }
                        )
                    except Exception as e:
                        print(e)

                    if conversation.autopilot:
                        past_messages = Message.objects.filter(conversation=conversation).order_by('-created_at')[:settings.AI_CONTEXT_SIZE]
                        past_messages = past_messages[::-1]
                        past_messages = MessageSerializer(past_messages, many=True).data
                        past_messages = json.dumps(past_messages)

                        try:
                            ai_response = get_my_ai_response(past_messages)
                            ai_user = Profile.objects.get(AI=True).user
                            ai_message = Message.objects.create(
                                                conversation=conversation,
                                                from_user=ai_user,
                                                message=ai_response,
                                                read=False
                                            )
                            
                        except Exception as e:
                            conversation.autopilot = False
                            conversation.save()
                            send_conversation_autopilot_deactivated(conversation)
                        
                        try:
                            channel_layer = get_channel_layer()
                            async_to_sync(channel_layer.group_send)(
                                conversation.name,
                                {
                                    'type': 'chat_message_echo',
                                    'sender': ai_user,
                                    'message': MessageSerializer(ai_message).data
                                }
                            )
                        except Exception as e:
                            print(e)
                            
                    return Response({'success': True}, status=status.HTTP_200_OK)