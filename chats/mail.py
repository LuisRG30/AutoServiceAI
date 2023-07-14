from users.mail import EmailThread
from django.conf import settings

from django.contrib.auth import get_user_model

from .models import Profile

User = get_user_model()

def send_payment_success_mail(payment):
    subject = 'Pago realizado con éxito'
    template = 'payment_success.html'

    context = {
        'user': payment.conversation.user,
        'domain': settings.SITE_DOMAIN,
        'payment': payment,
    }
    EmailThread(subject, template, [payment.conversation.user.email], context).start()

def send_payment_notification_admins(payment):
    subject = 'Nuevo pago realizado'
    template = 'payment_notification.html'

    context = {
        'user': payment.conversation.user,
        'domain': settings.SITE_DOMAIN,
        'payment': payment,
    }
    admins = Profile.objects.filter(admin=True)
    recipients = [admin.user.email for admin in admins]
    EmailThread(subject, template, recipients, context).start()

def send_message_notification(message):
    subject = 'Nuevo mensaje recibido'
    template = 'message_notification.html'

    context = {
        'user': message.conversation.user,
        'domain': settings.SITE_DOMAIN,
        'message': message,
    }
    sender = message.from_user
    assignee = message.conversation.assigned_to
    admins = Profile.objects.filter(admin=True)

    if not assignee:
        recipients = [admin.user.email for admin in admins]
        template = 'message_notification_no_assignee.html'
    elif sender == assignee:
        recipients = [message.conversation.user.email]
    else:
        recipients = [assignee.email]

    EmailThread(subject, template, recipients, context).start()

def send_document_upload_notification(document):
    subject = 'Nuevo documento recibido'
    template = 'document_upload_notification.html'

    context = {
        'user': document.conversation.user,
        'domain': settings.SITE_DOMAIN,
        'document': document,
    }

    recipients = [document.conversation.user.email]
    if document.conversation.assigned_to:
        recipients.append(document.conversation.assigned_to.email)

    EmailThread(subject, template, recipients, context).start()

def send_document_requested_notification(document):
    subject = 'Documento solicitado'
    template = 'document_requested_notification.html'

    context = {
        'user': document.conversation.assigned_to,
        'domain': settings.SITE_DOMAIN,
        'document': document,
    }
    recipients = [document.conversation.user.email]
    EmailThread(subject, template, recipients, context).start()

def send_payment_requested_notification(payment):
    subject = 'Pago solicitado'
    template = 'payment_requested_notification.html'

    context = {
        'user': payment.conversation.assigned_to,
        'domain': settings.SITE_DOMAIN,
        'payment': payment,
    }
    recipients = [payment.conversation.user.email]
    EmailThread(subject, template, recipients, context).start()

def send_new_conversation_notification_admins(conversation):
    subject = 'Nueva conversación iniciada'
    template = 'new_conversation_notification.html'

    context = {
        'user': conversation.user,
        'domain': settings.SITE_DOMAIN,
        'conversation': conversation,
    }
    admins = Profile.objects.filter(admin=True)
    recipients = [admin.user.email for admin in admins]
    EmailThread(subject, template, recipients, context).start()

def send_conversation_assignment_notification(conversation):
    subject = 'Conversación asignada'
    template = 'conversation_assignment_notification.html'

    context = {
        'user': conversation.user,
        'domain': settings.SITE_DOMAIN,
        'conversation': conversation,
    }
    admins = Profile.objects.filter(admin=True)
    recipients = [admin.user.email for admin in admins]
    EmailThread(subject, template, recipients, context).start()

def send_conversation_unassignment_notification(conversation):
    subject = 'Conversación desasignada'
    template = 'conversation_unassignment_notification.html'

    context = {
        'user': conversation.user,
        'domain': settings.SITE_DOMAIN,
        'conversation': conversation,
    }
    admins = Profile.objects.filter(admin=True)
    recipients = [admin.user.email for admin in admins]
    EmailThread(subject, template, recipients, context).start()

def send_conversation_archive_change_notification(conversation):
    subject = 'Conversación archivada'
    template = 'conversation_archive_change_notification.html'

    context = {
        'user': conversation.user,
        'domain': settings.SITE_DOMAIN,
        'conversation': conversation,
    }
    admins = Profile.objects.filter(admin=True)
    recipients = [admin.user.email for admin in admins]
    EmailThread(subject, template, recipients, context).start()

def send_conversation_autopilot_deactivated(conversation):
    subject = 'Autopilot desactivado'
    template = 'conversation_autopilot_deactivated.html'

    context = {
        'user': conversation.user,
        'domain': settings.SITE_DOMAIN,
        'conversation': conversation,
    }
    admins = Profile.objects.filter(admin=True)
    recipients = [admin.user.email for admin in admins]
    EmailThread(subject, template, recipients, context).start()