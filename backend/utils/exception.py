from http import HTTPStatus

from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    if response is not None and HTTPStatus.BAD_REQUEST:
        response.data = {'field_name': ['Обязательное поле.']}

    if response is not None and HTTPStatus.NOT_FOUND:
        response.data = {'detail': 'Страница не найдена.'}

    return response
