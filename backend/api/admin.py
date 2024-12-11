from django.contrib import admin

from api.models import (
    FavoriteRecipe,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    Subscription,
    Tag,
)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("user", "author")
    list_filter = ("user", "author")


@admin.register(ShoppingList)
class ShoppingListAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe")
    list_filter = ("user", "recipe")


@admin.register(FavoriteRecipe)
class FavoriteRecipeAdmin(admin.ModelAdmin):
    list_display = ("user", "recipe", "recipe_author")
    list_filter = ("user", "recipe", "recipe_author")

    def recipe_author(self, obj):
        return obj.recipe.author.username

    recipe_author.short_description = 'Автор рецепта'


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "measurement_unit")
    search_fields = ("name",)
    list_filter = ("measurement_unit",)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    min_num = 1


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ("name", "author", "cooking_time", "favorite_count")
    search_fields = ("name", "author__username")
    list_filter = ("tags",)
    inlines = (RecipeIngredientInline,)

    @admin.display(description='кол.во избранных')
    def favorite_count(self, obj):
        return obj.favorited_by.count()
