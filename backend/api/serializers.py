from rest_framework import serializers
from .models import Recipe, Ingredient, Tag, RecipeIngredient, Subscription, FavoriteRecipe, ShoppingList, User
import base64
from django.core.files.base import ContentFile


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = ('id', 'name', 'measurement_unit')


class TagSerializer(serializers.ModelSerializer):
    """Сериализатор для тегов."""
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        return super().to_internal_value(data)


class TagPrimaryKeySerializer(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return TagSerializer(value).data


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'amount']


class RecipeSerializer(serializers.ModelSerializer):
    ingredients = RecipeIngredientWriteSerializer(many=True, source='recipe_ingredients')
    tags = TagPrimaryKeySerializer(queryset=Tag.objects.all(), many=True)
    image = Base64ImageField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    author = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = ('id', 'name', 'text', 'ingredients', 'tags', 'image', 'cooking_time', 'author', 'is_favorited', 'is_in_shopping_cart')

    def get_author(self, obj):
        user = obj.author
        request_user = self.context['request'].user
        return {
            "email": user.email,
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_subscribed": Subscription.objects.filter(
                user=request_user, author=user
            ).exists() if request_user.is_authenticated else False,
            "avatar": user.avatar.url if user.avatar else None,
        }

    def validate_ingredients(self, value):
        if not value:
            raise serializers.ValidationError("Ингредиенты не могут быть пустыми.")
        ingredients_set = set()
        for ingredient in value:
            if ingredient['id'] in ingredients_set:
                raise serializers.ValidationError("Ингредиенты должны быть уникальными.")
            ingredients_set.add(ingredient['id'])
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError("Количество ингредиента должно быть больше 0.")
        return value

    def create_ingredients(self, ingredients, recipe):
        RecipeIngredient.objects.bulk_create([
            RecipeIngredient(
                ingredient_id=ingredient['id'],
                recipe=recipe,
                amount=ingredient['amount']
            ) for ingredient in ingredients
        ])

    def create(self, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', [])
        tags_data = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('recipe_ingredients', [])
        tags_data = validated_data.pop('tags', [])
        instance = super().update(instance, validated_data)
        instance.tags.set(tags_data)
        instance.recipe_ingredients.all().delete()
        self.create_ingredients(ingredients_data, instance)
        return instance

    def to_representation(self, instance):
        """Переопределение, чтобы отобразить данные после создания/обновления."""
        context = self.context
        return RecipeDetailSerializer(instance, context=context).data


class RecipeDetailSerializer(serializers.ModelSerializer):
    author = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    def get_author(self, obj):
        user = obj.author
        request_user = self.context['request'].user
        return {
            "email": user.email,
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "is_subscribed": Subscription.objects.filter(
                user=request_user, author=user
            ).exists() if request_user.is_authenticated else False,
            "avatar": user.avatar.url if user.avatar else None,
        }

    def get_ingredients(self, obj):
        return [
            {
                "id": item.ingredient.id,
                "name": item.ingredient.name,
                "measurement_unit": item.ingredient.measurement_unit,
                "amount": item.amount,
            }
            for item in obj.recipe_ingredients.all()
        ]

    def get_is_favorited(self, obj):
        user = self.context['request'].user
        return (
            FavoriteRecipe.objects.filter(user=user, recipe=obj).exists()
            if user.is_authenticated
            else False
        )

    def get_is_in_shopping_cart(self, obj):
        user = self.context['request'].user
        return (
            ShoppingList.objects.filter(user=user, recipe=obj).exists()
            if user.is_authenticated
            else False
        )

    class Meta:
        model = Recipe
        fields = (
            "id",
            "tags",
            "author",
            "ingredients",
            "is_favorited",
            "is_in_shopping_cart",
            "name",
            "image",
            "text",
            "cooking_time",
        )


class SimpleRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']

class SubscriptionSerializer(serializers.ModelSerializer):
    author = serializers.SlugRelatedField(slug_field="username", read_only=True)

    class Meta:
        model = Subscription
        fields = ["id", "user", "author"]

class SubscriptionDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="author.username")
    first_name = serializers.CharField(source="author.first_name")
    last_name = serializers.CharField(source="author.last_name")
    email = serializers.EmailField(source="author.email")
    is_subscribed = serializers.SerializerMethodField()
    avatar = serializers.ImageField(source="author.avatar", required=False)
    recipes_count = serializers.IntegerField(source="author.recipes.count", read_only=True)
    recipes = serializers.SerializerMethodField()

    class Meta:
        model = Subscription
        fields = [
            'id', 'username', 'first_name', 'last_name', 'email',
            'is_subscribed', 'avatar', 'recipes_count', 'recipes'
        ]

    def get_is_subscribed(self, obj):
        """Проверяет, подписан ли текущий пользователь на автора."""
        user = self.context['request'].user
        return Subscription.objects.filter(user=user, author=obj.author).exists()

    def get_recipes(self, obj):
        """Возвращает ограниченный список рецептов автора."""
        limit = self.context['request'].query_params.get('recipes_limit')  # Параметр recipes_limit из запроса
        recipes = obj.author.recipes.all()
        if limit:
            try:
                limit = int(limit)
                recipes = recipes[:limit]
            except ValueError:
                pass
        # Используем упрощённый сериализатор
        return SimpleRecipeSerializer(recipes, many=True, context=self.context).data


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(source='recipe.id', read_only=True)
    name = serializers.CharField(source='recipe.name', read_only=True)
    image = serializers.ImageField(source='recipe.image', read_only=True)
    cooking_time = serializers.IntegerField(source='recipe.cooking_time', read_only=True)

    class Meta:
        model = FavoriteRecipe
        fields = ["id", "name", "image", "cooking_time"]


class ShoppingListSerializer(serializers.ModelSerializer):
    """Сериализатор для корзины покупок."""
    recipe = SimpleRecipeSerializer(read_only=True)

    class Meta:
        model = ShoppingList
        fields = ['recipe']  # Убираем id, так как он не нужен в ответе

    def to_representation(self, instance):
        """Извлекаем данные о рецепте вместо ключа `recipe`."""
        representation = super().to_representation(instance)
        return representation['recipe']  # Возвращаем только данные о рецепте
