import datetime
import logging as log
import os

import requests

from ..apis.default_api_base import BaseDefaultApi
from ..models.get_greeting200_response import (
    GetGreeting200Response,
    GetGreeting200ResponseTgBotThing,
)
from ..models.send_message_request import SendMessageRequest


class DefaultApiImpl(BaseDefaultApi):
    async def get_greeting(self) -> GetGreeting200Response:
        return GetGreeting200Response(message='hello from telegramm', current_time=datetime.datetime.now(), tg_bot_thing=GetGreeting200ResponseTgBotThing(test_prop='sheesh'))

    async def send_message(self, send_message_request: SendMessageRequest):
        token = os.getenv('TG_TOKEN')
        payload = {
            'chat_id': send_message_request.chat_id,
            'text': send_message_request.message_text,
            'parse_mode': 'HTML'
        }

        response = requests.post(url=f'https://api.telegram.org/bot{token}/sendMessage', data=payload)
        if not response.json['ok']:
            raise RuntimeError(response.json['description'])
