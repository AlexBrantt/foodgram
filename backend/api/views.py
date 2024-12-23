import base64
import hashlib

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db.models import Count, Sum
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.filters import IngredientFilter, RecipeFilter
from api.models import (
    FavoriteRecipe,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    Subscription,
    Tag,
)
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    FavoriteRecipeSerializer,
    IngredientSerializer,
    RecipeDetailSerializer,
    RecipeSerializer,
    ShoppingListSerializer,
    SubscriptionDetailSerializer,
    SubscriptionSerializer,
    TagSerializer,
    UserListSerializer,
    UserRegistrationSerializer,
)
from utils.pagination import CustomPageNumberPagination, SubscriptionPagination

User = get_user_model()


class ShortLinkView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, id):
        try:
            _ = get_object_or_404(Recipe, id=id)
            url = f"{request.scheme}://{request.META['HTTP_HOST']}"
            short = f"{url}/s/{hashlib.md5(str(id).encode()).hexdigest()[:5]}"
            return Response({"short-link": short}, status=status.HTTP_200_OK)

        except Http404:
            return Response(
                {"detail": "Страница не найдена."},
                status=status.HTTP_404_NOT_FOUND,
            )


class RecipeViewSet(ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'tags', 'recipe_ingredients__ingredient'
    )
    permission_classes = [IsAuthorOrReadOnly]
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RecipeDetailSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class TagViewSet(ReadOnlyModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [AllowAny]
    pagination_class = None


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    permission_classes = [AllowAny]
    pagination_class = None
    filter_backends = [DjangoFilterBackend]
    filterset_class = IngredientFilter


class SubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        queryset = User.objects.annotate(recipes_count=Count('recipes')).all()
        author = get_object_or_404(queryset, id=id)

        if request.user == author:
            return Response(
                {"error": "Нельзя подписаться на самого себя"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Subscription.objects.filter(
            user=request.user, author=author
        ).exists():
            return Response(
                {"error": "Вы уже подписаны на этого автора"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = {'author': author.id, 'user': request.user.id}
        serializer = SubscriptionSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        serializer = SubscriptionDetailSerializer(
            author,
            context={
                'request': request,
                'limit': request.query_params.get('limit'),
            },
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        author = get_object_or_404(User, id=id)

        deleted_count, _ = Subscription.objects.filter(
            user=request.user, author=author
        ).delete()

        if deleted_count == 0:
            return Response(
                {"error": "Вы не подписаны на этого автора"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        subscriptions = Subscription.objects.filter(user=user).values('author')
        authors = User.objects.filter(id__in=subscriptions).annotate(
            recipes_count=Count('recipes')
        )
        paginator = SubscriptionPagination()
        paginated_subscriptions = paginator.paginate_queryset(authors, request)

        serializer = SubscriptionDetailSerializer(
            paginated_subscriptions, many=True, context={'request': request}
        )

        return paginator.get_paginated_response(serializer.data)


class FavoriteRecipeView(APIView):
    def post(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)

        if FavoriteRecipe.objects.filter(
            user=request.user, recipe=recipe
        ).exists():
            return Response(
                {"error": "Рецепт уже в избранном"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        favorite = FavoriteRecipe.objects.create(
            user=request.user, recipe=recipe
        )

        serializer = FavoriteRecipeSerializer(favorite)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)

        try:
            favorite = FavoriteRecipe.objects.get(
                user=request.user, recipe=recipe
            )
            favorite.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except FavoriteRecipe.DoesNotExist:
            return Response(
                {"error": "Рецепт отсутствует в избранном"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class ShoppingCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)

        if ShoppingList.objects.filter(
            user=request.user, recipe=recipe
        ).exists():
            return Response(
                {"error": "Рецепт уже в списке покупок"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shopping_item = ShoppingList.objects.create(
            user=request.user, recipe=recipe
        )

        serializer = ShoppingListSerializer(shopping_item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)
        try:
            shopping_item = ShoppingList.objects.get(
                user=request.user, recipe=recipe
            )
            shopping_item.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except ShoppingList.DoesNotExist:
            return Response(
                {"error": "Рецепт отсутствует в списке покупок"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DownloadShoppingCartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        ingredients_list = (
            RecipeIngredient.objects.filter(
                recipe__in_shopping_lists__user=user
            )
            .values('ingredient__name', 'ingredient__measurement_unit')
            .annotate(amount=Sum('amount'))
            .order_by('ingredient__name', 'ingredient__measurement_unit')
        )

        content = "\n".join(
            [
                f"{row['ingredient__name']} — {row['amount']} "
                f"{row['ingredient__measurement_unit']}"
                for row in ingredients_list
            ]
        )

        response = HttpResponse(content, content_type="text/plain")
        response['Content-Disposition'] = (
            'attachment; ' 'filename="shopping_list.txt"'
        )
        return response


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
        url_path='me/avatar',
    )
    def avatar(self, request):
        """Обновление или удаление аватарки для текущего пользователя."""
        user = request.user

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
