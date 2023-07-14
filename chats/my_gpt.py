import requests
from django.conf import settings


def get_my_ai_response(past_messages):
    url = settings.MY_GPT_URL
    headers = {
        "Content-Type": "application/json",
    }
    try:
        r = requests.post(url, json=past_messages, headers=headers)
        return r.json()
    except requests.exceptions.HTTPError as err:
        return "Error"
        