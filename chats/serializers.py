from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.contrib.auth.password_validation import validate_password
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Integration, Conversation, Message, Document, Payment, Profile

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    name = serializers.CharField(max_length=50, write_only=True, required=True)
    surname = serializers.CharField(max_length=50, write_only=True, required=True)
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password], style={'input_type': 'password'})
    confirm_password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    auth_token = serializers.SerializerMethodField('get_auth_token', read_only=True)

    class Meta:
        model = User
        fields = ('email', 'phone', 'name', 'surname', 'password', 'confirm_password', 'auth_token')

    def validate(self, attrs):  
        if attrs['password'] != attrs['confirm_password']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."})
        if 'name' not in attrs:
            raise serializers.ValidationError(
                {"name": "Name is required."})
        if 'surname' not in attrs:
            raise serializers.ValidationError(
                {"surname": "Surname is required."})
        try:
            email = attrs['email']
            if email:
                validate_email(email)
        except:
            raise serializers.ValidationError(
                {"email": "Invalid email"})
        return attrs
    
    def get_auth_token(self, obj):
        data = {}
        token_class = RefreshToken
        token = token_class.for_user(obj)
        data['refresh'] = str(token)
        data['access'] = str(token.access_token)
        return data

    def create(self, validated_data):
        user = User.objects.create(
            email = validated_data['email'],
            phone = validated_data['phone'],
            first_name = validated_data['name'],
            last_name = validated_data['surname'],
        )
        user.set_password(validated_data['password'])
        user.save()
        return user
    
class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ('admin',)


class UserSerializer(serializers.ModelSerializer):
    profile = ProfileSerializer()
    class Meta:
        model = User
        fields = ('id', 'email', 'phone', 'first_name', 'last_name', 'profile')

class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Document
        fields = ('id', 'name', 'file', 'message', 'conversation', 'staging', 'created_at', 'updated_at')

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ('id', 'description', 'amount_cents', 'paid', 'created_at')

class MessageSerializer(serializers.ModelSerializer):
    from_user = UserSerializer()
    document = DocumentSerializer()
    payment = PaymentSerializer()
    class Meta:
        model = Message
        fields = ('id', 'conversation', 'from_user', 'message', 'read', 'image', 'document', 'payment', 'created_at')

class IntegrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Integration
        fields = ('id', 'channel', 'whatsapp_token', 'telegram_token', 'web_token')

class ConversationSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    last_message = MessageSerializer(read_only=True)
    integration = IntegrationSerializer(read_only=True)
    class Meta:
        model = Conversation
        fields = ('id', 'integration', 'user', 'name', 'status', 'archived', 'autopilot' ,'created_at', 'updated_at', 'assigned_to', 'last_message')
        read_only_fields = ('name',)

