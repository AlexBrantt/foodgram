from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (RecipeViewSet, IngredientViewSet,
                    TagViewSet, SubscribeView, FavoriteRecipeView,
                    ShoppingCartView, SubscriptionListView, ShortLinkView,
                    TagListView, IngredientListView, DownloadShoppingCartView)

router = DefaultRouter()
router.register(r'recipes', RecipeViewSet, basename='recipe')

urlpatterns = [
    path("users/<int:id>/subscribe/", SubscribeView.as_view(), name="subscribe"),
    path('users/subscriptions/', SubscriptionListView.as_view(), name='subscription_list'),

    path('recipes/download_shopping_cart/', DownloadShoppingCartView.as_view(), name='download_shopping_cart'),
    path("", include(router.urls)),
    path("recipes/<int:id>/favorite/", FavoriteRecipeView.as_view(), name="favorite_recipe"),
    path("recipes/<int:id>/shopping_cart/", ShoppingCartView.as_view(), name="shopping_cart"),

    path('recipes/<int:id>/get-link/', ShortLinkView.as_view(), name='get_short_link'),

    path('tags/', TagListView.as_view(), name='tags-list'),
    path('tags/<int:pk>/', TagViewSet.as_view({'get': 'retrieve'}), name='tags-detail'),

    path('ingredients/', IngredientListView.as_view(), name='ingredients-list'),
    path('ingredients/<int:pk>/', IngredientViewSet.as_view({'get': 'retrieve'}), name='ingredients-detail'),
]
