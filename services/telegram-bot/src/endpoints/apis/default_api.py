# coding: utf-8

from typing import Dict, List  # noqa: F401
import importlib
import pkgutil

from endpoints.apis.default_api_base import BaseDefaultApi
import endpoints

from fastapi import (  # noqa: F401
    APIRouter,
    Body,
    Cookie,
    Depends,
    Form,
    Header,
    HTTPException,
    Path,
    Query,
    Response,
    Security,
    status,
)

from endpoints.models.extra_models import TokenModel  # noqa: F401
from typing import Any
from endpoints.models.get_greeting200_response import GetGreeting200Response
from endpoints.models.send_message_request import SendMessageRequest


router = APIRouter()

ns_pkg = endpoints
for _, name, _ in pkgutil.iter_modules(ns_pkg.__path__, ns_pkg.__name__ + "."):
    importlib.import_module(name)


@router.get(
    "/telegram-bot/ping",
    responses={
        200: {"model": GetGreeting200Response, "description": "Successful response"},
    },
    tags=["default"],
    summary="Returns a greeting and the current time",
    response_model_by_alias=True,
)
async def get_greeting(
) -> GetGreeting200Response:
    if not BaseDefaultApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseDefaultApi.subclasses[0]().get_greeting()


@router.post(
    "/telegram-bot/internal/send",
    responses={
        204: {"description": "Ok"},
        400: {"description": "Bad Request"},
        404: {"description": "Not Found"},
    },
    tags=["default"],
    summary="Send message to the user",
    response_model_by_alias=True,
)
async def send_message(
    send_message_request: SendMessageRequest = Body(None, description=""),
) -> None:
    if not BaseDefaultApi.subclasses:
        raise HTTPException(status_code=500, detail="Not implemented")
    return await BaseDefaultApi.subclasses[0]().send_message(send_message_request)
