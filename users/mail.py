import threading
from django.conf import settings

from django.core.mail import EmailMessage
from django.template.loader import get_template
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import account_activation_token, password_reset_token

class EmailThread(threading.Thread):
    def __init__(self, subject, template, recipient_list, context={}):
        self.subject = subject
        self.recipient_list = recipient_list
        self.template = template
        self.context = context
        threading.Thread.__init__(self)

    def run (self):
        message = get_template(self.template).render(self.context)
        msg = EmailMessage(self.subject, message, settings.EMAIL_HOST_USER, self.recipient_list)
        msg.content_subtype = "html"
        msg.send()


def send_password_reset_mail(user):
    subject = 'Restablece tu contraseña'
    template = 'password_reset.html'

    context = {
        'user': user,
        'domain': settings.SITE_DOMAIN,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'token': password_reset_token.make_token(user),
    }
    EmailThread(subject, template, [user.email], context).start()