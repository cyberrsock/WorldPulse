# coding: utf-8

from typing import ClassVar, Dict, List, Tuple  # noqa: F401

from typing import Any
from endpoints.models.get_greeting200_response import GetGreeting200Response
from endpoints.models.send_message_request import SendMessageRequest


class BaseDefaultApi:
    subclasses: ClassVar[Tuple] = ()

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        BaseDefaultApi.subclasses = BaseDefaultApi.subclasses + (cls,)
    async def get_greeting(
        self,
    ) -> GetGreeting200Response:
        ...


    async def send_message(
        self,
        send_message_request: SendMessageRequest,
    ) -> None:
        ...
