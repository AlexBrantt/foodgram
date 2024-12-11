import hashlib

from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.filters import SearchFilter
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import (
    IsAuthenticated,
    IsAuthenticatedOrReadOnly,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from api.filters import RecipeFilter
from api.models import (
    FavoriteRecipe,
    Ingredient,
    Recipe,
    ShoppingList,
    Subscription,
    Tag,
    User,
)
from api.serializers import (
    FavoriteRecipeSerializer,
    IngredientSerializer,
    RecipeDetailSerializer,
    RecipeSerializer,
    ShoppingListSerializer,
    SubscriptionDetailSerializer,
    TagSerializer,
)
from utils.pagination import CustomPageNumberPagination


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
    queryset = Recipe.objects.prefetch_related(
        'tags', 'recipe_ingredients__ingredient'
    )
    permission_classes = [IsAuthenticatedOrReadOnly]
    pagination_class = CustomPageNumberPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = RecipeFilter

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return RecipeDetailSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
        recipe = self.get_object()
        if recipe.author != self.request.user:
            raise PermissionDenied("Вы не можете изменять чужой рецепт.")
        serializer.save()

    def perform_destroy(self, instance):
        if instance.author != self.request.user:
            raise PermissionDenied("Вы не можете удалить чужой рецепт.")
        instance.delete()

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)

        if page is not None:
            serializer = RecipeDetailSerializer(
                page, many=True, context={'request': request}
            )
            return self.get_paginated_response(serializer.data)

        serializer = RecipeDetailSerializer(
            queryset, many=True, context={'request': request}
        )
        return Response(serializer.data)


class TagViewSet(ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class TagListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        tags = Tag.objects.all()
        serializer = TagSerializer(tags, many=True)
        return Response(serializer.data)


class IngredientViewSet(ReadOnlyModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['measurement_unit']
    search_fields = ['=name']


class IngredientListView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, *args, **kwargs):
        name_filter = request.query_params.get('name', '').lower()
        if name_filter:
            ingredients = Ingredient.objects.filter(
                name__istartswith=name_filter
            )
        else:
            ingredients = Ingredient.objects.all()
        serializer = IngredientSerializer(ingredients, many=True)
        return Response(serializer.data)


class SubscribeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, id):
        author = get_object_or_404(User, id=id)

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

        subscription = Subscription.objects.create(
            user=request.user, author=author
        )

        serializer = SubscriptionDetailSerializer(
            subscription,
            context={
                'request': request,
                'limit': request.query_params.get('limit'),
            },
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def delete(self, request, id):
        author = get_object_or_404(User, id=id)

        try:
            subscription = Subscription.objects.get(
                user=request.user, author=author
            )
            subscription.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Subscription.DoesNotExist:
            return Response(
                {"error": "Вы не подписаны на этого автора"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class SubscriptionPagination(PageNumberPagination):
    def get_page_size(self, request):
        try:
            return int(request.query_params.get('limit', self.page_size))
        except (TypeError, ValueError):
            return self.page_size


class SubscriptionListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        subscriptions = Subscription.objects.filter(user=user)

        paginator = SubscriptionPagination()
        paginated_subscriptions = paginator.paginate_queryset(
            subscriptions, request
        )

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
        shopping_list = ShoppingList.objects.filter(user=user)
        ingredients = {}

        for item in shopping_list:
            for recipe_ingredient in item.recipe.recipe_ingredients.all():
                ingredient = recipe_ingredient.ingredient
                amount = recipe_ingredient.amount
                name = ingredient.name
                measurement_unit = ingredient.measurement_unit

                if name not in ingredients:
                    ingredients[name] = {
                        'amount': amount,
                        'measurement_unit': measurement_unit,
                    }
                else:
                    ingredients[name]['amount'] += amount

        content = "\n".join(
            [
                f"{name} ({data['measurement_unit']}) — {data['amount']}"
                for name, data in ingredients.items()
            ]
        )

        # Ответ в формате .txt
        response = HttpResponse(content, content_type="text/plain")
        response['Content-Disposition'] = (
            'attachment; ' 'filename="shopping_list.txt"'
        )
        return response
