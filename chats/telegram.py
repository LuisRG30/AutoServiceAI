import requests
from django.conf import settings

TELEGRAM_TOKEN = settings.TELEGRAM_TOKEN

def send_telegram(chat_id, message):
  url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
  json = {
    "chat_id": chat_id,
    "text": message,
  }
  try:
    r = requests.post(url, json=json)
  except requests.exceptions.HTTPError as err:
    print(err)