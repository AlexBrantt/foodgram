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


admin.site.register(Subscription)
admin.site.register(ShoppingList)
admin.site.register(FavoriteRecipe)
