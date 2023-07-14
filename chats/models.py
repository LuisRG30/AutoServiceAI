from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth import get_user_model

User = get_user_model()     

STATUS_CHOICES = (
    ('active', 'Activo'),
    ('inactive', 'Inactivo'),
    ('blocked', 'Bloqueado'),
    ('urgent', 'Urgente'),
    ('resolved', 'Resuelto')
)

CHANNEL_CHOICES = (
    ('integrated', 'Integrado'),
    ('whatsapp', 'WhatsApp'),
    ('telegram', 'Telegram'),
    ('web', 'Web'),
)

class Integration(models.Model):
    channel = models.CharField(max_length=255, choices=CHANNEL_CHOICES, default='integrated')
    telegram_token = models.CharField(max_length=255, blank=True, null=True)
    whatsapp_token = models.CharField(max_length=255, blank=True, null=True)
    web_token = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.channel


class Conversation(models.Model):
    name = models.CharField(max_length=255)
    integration = models.OneToOneField(Integration, on_delete=models.CASCADE)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, related_name="conversation", blank=True, null=True)
    assigned_to = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name="assigned_conversations")
    status = models.CharField(max_length=255, choices=STATUS_CHOICES, default='inactive')
    archived = models.BooleanField(default=False)
    autopilot = models.BooleanField(default=True)
    score = models.FloatField(default=1.0, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def last_message(self):
        return self.messages.last()
    
class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    from_user = models.ForeignKey(User, on_delete=models.CASCADE)
    message = models.TextField(blank=True, null=True)
    image = models.ImageField(blank=True, null=True)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.from_user.email} - {self.created_at}"

class Document(models.Model):
    name = models.CharField(max_length=255, blank=True, null=True)
    file = models.FileField(blank=True, null=True)
    message = models.OneToOneField(Message, on_delete=models.SET_NULL, blank=True, null=True, related_name="document")
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    staging = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.conversation}: {self.name}"

class Payment(models.Model):
    message = models.OneToOneField(Message, on_delete=models.SET_NULL, blank=True, null=True, related_name="payment")
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    description = models.CharField(max_length=512)
    amount_cents = models.IntegerField()
    paid = models.BooleanField(default=False)
    date_paid = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.conversation}: {self.amount_cents}"
    
class PaymentIntent(models.Model):
    payment_intent_id = models.CharField(max_length=255)
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, related_name="payment_intents")

    def __str__(self):
        return f"{self.payment_intent_id}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    admin = models.BooleanField(default=False)
    AI = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email

def create_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

post_save.connect(create_profile, sender=User)