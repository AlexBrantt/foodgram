import hashlib

from django.contrib.auth import get_user_model
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from djoser.views import UserViewSet
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
from api.permissions import IsAuthorOrReadOnly
from api.serializers import (
    AvatarSerializer,
    FavoriteRecipeSerializer,
    IngredientSerializer,
    RecipeDetailSerializer,
    RecipeSerializer,
    ShoppingListSerializer,
    SubscriptionDetailSerializer,
    SubscriptionSerializer,
    TagSerializer,
)
from recipes.models import (
    FavoriteRecipe,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    Subscription,
    Tag,
)
from utils.pagination import CustomPageNumberPagination

User = get_user_model()


class ShortLinkView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, id):
        _ = get_object_or_404(Recipe, id=id)
        url = f"{request.scheme}://{request.META['HTTP_HOST']}"
        short = f"{url}/s/{hashlib.md5(str(id).encode()).hexdigest()[:5]}"
        return Response({'short-link': short}, status=status.HTTP_200_OK)


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
        queryset = User.objects.annotate(
            recipes_count=Count('recipe_author')
        ).all()
        author = get_object_or_404(queryset, id=id)
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
        deleted_count, _ = Subscription.objects.filter(
            user=request.user, author_id=id, author__isnull=False
        ).delete()

        if deleted_count == 0:
            if not User.objects.filter(id=id).exists():
                return Response(
                    {'error': 'Автор не найден'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(
                {'error': 'Вы не подписаны на этого автора'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_204_NO_CONTENT)


class SubscriptionListView(ModelViewSet):
    queryset = User.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    serializer_class = SubscriptionDetailSerializer

    def list(self, request, *args, **kwargs):
        user = request.user
        subscriptions = Subscription.objects.filter(user=user).values('author')
        authors = self.queryset.filter(id__in=subscriptions).annotate(
            recipes_count=Count('recipe_author')
        )

        serializer = SubscriptionDetailSerializer(
            self.paginate_queryset(authors),
            many=True,
            context={'request': request},
        )

        return self.get_paginated_response(serializer.data)


class FavoriteRecipeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)
        data = {'recipe': recipe.id, 'user': request.user.id}
        serializer = FavoriteRecipeSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)
        deleted, _ = FavoriteRecipe.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Рецепт отсутствует в избранном'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class ShoppingCartView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)
        data = {'recipe': recipe.id, 'user': request.user.id}
        serializer = ShoppingListSerializer(
            data=data, context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        recipe = get_object_or_404(Recipe, id=id)
        deleted, _ = ShoppingList.objects.filter(
            user=request.user, recipe=recipe
        ).delete()
        if deleted:
            return Response(status=status.HTTP_204_NO_CONTENT)
        return Response(
            {'error': 'Рецепт отсутствует в избранном'},
            status=status.HTTP_400_BAD_REQUEST,
        )


class DownloadShoppingCartView(APIView):
    permission_classes = [IsAuthenticated]

    def content_prepare(self, ingredients):
        return '\n'.join(
            [
                f"{row['ingredient__name']} — {row['amount']} "
                f"{row['ingredient__measurement_unit']}"
                for row in ingredients
            ]
        )

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
        response = HttpResponse(
            self.content_prepare(ingredients_list), content_type='text/plain'
        )
        response['Content-Disposition'] = (
            'attachment; ' 'filename="shopping_list.txt"'
        )
        return response


class CustomUserViewSet(UserViewSet):
    permission_classes = [AllowAny]
    pagination_class = CustomPageNumberPagination

    @action(
        detail=False, methods=['get'], permission_classes=[IsAuthenticated]
    )
    def me(self, request, *args, **kwargs):
        """Возвращает профиль текущего пользователя."""
        return Response(
            self.get_serializer(request.user).data, status=status.HTTP_200_OK
        )

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
            serializer = AvatarSerializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            user.avatar.save(
                serializer.validated_data['avatar'].name,
                serializer.validated_data['avatar'],
                save=True,
            )
            return Response(
                {'avatar': user.avatar.url}, status=status.HTTP_200_OK
            )

        # Удаление аватарки
        if user.avatar:
            user.avatar.delete()
            return Response(
                {'detail': 'Аватарка удалена.'}, status.HTTP_204_NO_CONTENT
            )
        return Response(
            {'detail': 'Аватарка не найдена.'}, status.HTTP_400_BAD_REQUEST
        )
