from django.contrib import admin

from .models import Conversation, Message, Document, Payment, PaymentIntent, Profile

admin.site.register(Conversation)
admin.site.register(Message)
admin.site.register(Document)
admin.site.register(Payment)
admin.site.register(PaymentIntent)
admin.site.register(Profile)