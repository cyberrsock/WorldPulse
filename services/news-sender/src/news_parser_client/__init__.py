# coding: utf-8

# flake8: noqa

"""
    news-parser

    Парсер новостей из тг каналов

    The version of the OpenAPI document: 1.0.0
    Generated by OpenAPI Generator (https://openapi-generator.tech)

    Do not edit the class manually.
"""  # noqa: E501


__version__ = "1.0.0"

# import apis into sdk package
from news_parser_client.api.default_api import DefaultApi

# import ApiClient
from news_parser_client.api_response import ApiResponse
from news_parser_client.api_client import ApiClient
from news_parser_client.configuration import Configuration
from news_parser_client.exceptions import OpenApiException
from news_parser_client.exceptions import ApiTypeError
from news_parser_client.exceptions import ApiValueError
from news_parser_client.exceptions import ApiKeyError
from news_parser_client.exceptions import ApiAttributeError
from news_parser_client.exceptions import ApiException

# import models into sdk package
from news_parser_client.models.get_greeting200_response import GetGreeting200Response
