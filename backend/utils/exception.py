from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)

    # Обрабатываем ошибку 400
    if response is not None and response.status_code == 400:
        response.data = {"field_name": ["Обязательное поле."]}

    # Обрабатываем ошибку 404
    if response is not None and response.status_code == 404:
        response.data = {"detail": "Страница не найдена."}

    return response
