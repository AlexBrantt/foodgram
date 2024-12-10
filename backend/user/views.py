import base64

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from rest_framework.decorators import action
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from user.serializers import UserListSerializer, UserRegistrationSerializer
from utils.pagination import CustomPageNumberPagination

User = get_user_model()


class CustomUserViewSet(ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return UserListSerializer
        return UserRegistrationSerializer

    @action(
        detail=False, methods=['get'], permission_classes=[IsAuthenticated]
    )
    def me(self, request):
        """Возвращает профиль текущего пользователя."""
        serializer = UserListSerializer(
            request.user, context={'request': request}
        )
        return Response(serializer.data)

    @action(
        detail=False,
        methods=['put', 'delete'],
        permission_classes=[IsAuthenticated],
    )
    def avatar(self, request):
        """Обновление или удаление аватарки для текущего пользователя."""
        user = request.user
        if user.is_anonymous:
            raise AuthenticationFailed("Пользователь не аутентифицирован.")

        if request.method == 'PUT':
            # Обновление аватарки
            avatar_data = request.data.get('avatar')
            if not avatar_data:
                return Response(
                    {"detail": "Поле Avatar обязательное."}, status=400
                )

            try:
                format, imgstr = avatar_data.split(';base64,')
                ext = format.split('/')[1]
                img_data = base64.b64decode(imgstr)
                avatar_file = ContentFile(img_data, name=f"avatar.{ext}")
                user.avatar.save(avatar_file.name, avatar_file, save=True)
            except Exception as e:
                raise ValidationError(
                    f"Ошибка при обработке аватарки: {str(e)}"
                )

            return Response({"avatar": user.avatar.url})

        # Удаление аватарки
        if user.avatar:
            user.avatar.delete()
            return Response({"detail": "Аватарка удалена."}, status=204)
        return Response({"detail": "Аватарка не найдена."}, status=400)


class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        current_password = request.data.get("current_password")
        new_password = request.data.get("new_password")

        if not user.check_password(current_password):
            return Response({"detail": "Неверный пароль."}, status=400)

        try:
            validate_password(new_password, user)
        except ValidationError as e:
            raise ValidationError(
                f"Пароль не удовлетворяет требованиям: {', '.join(e.messages)}"
            )

        user.set_password(new_password)
        user.save()

        return Response(status=204)
