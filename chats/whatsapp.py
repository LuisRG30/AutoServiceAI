import requests
from django.conf import settings

WHATSAPP_NUMBER_IDENTIFIER = settings.WHATSAPP_NUMBER_IDENTIFIER
ACCESS_TOKEN = settings.WHATSAPP_ACCESS_TOKEN

def send_whatsapp(phone_number, message):
  url = f"https://graph.facebook.com/v17.0/{WHATSAPP_NUMBER_IDENTIFIER}/messages"

  headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {ACCESS_TOKEN}"
  }

  json = {
    "messaging_product": "whatsapp",
    "recipient_type": "individual",
    "to": phone_number[:2] + phone_number[3:],
    "type": "text",
    "text": {"body": message,
             "preview_url": "true"},
  }
  
  try:
    r = requests.post(url, json=json, headers=headers)
  except requests.exceptions.HTTPError as err:
    print(err)