import base64

from django.core.files.base import ContentFile
from rest_framework import serializers

from recipes.models import (
    FavoriteRecipe,
    Ingredient,
    Recipe,
    RecipeIngredient,
    ShoppingList,
    Subscription,
    Tag,
    User,
)


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


class AvatarSerializer(serializers.Serializer):
    avatar = Base64ImageField()


class TagPrimaryKeySerializer(serializers.PrimaryKeyRelatedField):
    def to_representation(self, value):
        return TagSerializer(value).data


class RecipeIngredientWriteSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField()

    class Meta:
        model = RecipeIngredient
        fields = ['id', 'amount']


class SimpleRecipeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Recipe
        fields = ['id', 'name', 'image', 'cooking_time']


class RecipeDetailSerializer(SimpleRecipeSerializer):
    author = serializers.SerializerMethodField()
    tags = TagSerializer(many=True, read_only=True)
    ingredients = serializers.SerializerMethodField()
    is_favorited = serializers.SerializerMethodField()
    is_in_shopping_cart = serializers.SerializerMethodField()
    image = Base64ImageField()

    class Meta(SimpleRecipeSerializer.Meta):
        fields = SimpleRecipeSerializer.Meta.fields + [
            'tags',
            'author',
            'ingredients',
            'is_favorited',
            'is_in_shopping_cart',
            'text',
        ]

    def get_author(self, obj):
        user = obj.author
        request_user = self.context['request'].user
        return {
            'email': user.email,
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_subscribed': (
                Subscription.objects.filter(
                    user=request_user, author=user
                ).exists()
                if request_user.is_authenticated
                else False
            ),
            'avatar': user.avatar.url if user.avatar else None,
        }

    def get_ingredients(self, obj):
        return [
            {
                'id': item.ingredient.id,
                'name': item.ingredient.name,
                'measurement_unit': item.ingredient.measurement_unit,
                'amount': item.amount,
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


class RecipeSerializer(RecipeDetailSerializer):
    ingredients = RecipeIngredientWriteSerializer(many=True)
    tags = TagPrimaryKeySerializer(queryset=Tag.objects.all(), many=True)

    def validate(self, attrs):
        ingredients = attrs.get('ingredients', [])
        if not ingredients:
            raise serializers.ValidationError(
                'Ингредиенты не могут быть пустыми'
            )

        ingredients_ids = [ingredient['id'] for ingredient in ingredients]
        if len(ingredients) != len(set(ingredients_ids)):
            raise serializers.ValidationError(
                'Ингредиенты должны быть уникальными'
            )

        tags = attrs.get('tags', [])
        if not tags:
            raise serializers.ValidationError('Теги не могут быть пустыми')

        if len(tags) != len(set(tags)):
            raise serializers.ValidationError('Теги должны быть уникальными')

        cooking_time = attrs.get('cooking_time', 0)
        if cooking_time == 0 or cooking_time < 1:
            raise serializers.ValidationError(
                'Время приготовления не может быть меньше единицы'
            )

        return attrs

    def validate_ingredients(self, value):
        for ingredient in value:
            if not Ingredient.objects.filter(pk=ingredient['id']).exists():
                raise serializers.ValidationError('Игредиент не существует')
            if ingredient['amount'] <= 0:
                raise serializers.ValidationError(
                    'Количество ингредиента должно быть больше 0.'
                )
        return value

    def create_ingredients(self, ingredients, recipe):
        RecipeIngredient.objects.bulk_create(
            [
                RecipeIngredient(
                    ingredient_id=ingredient['id'],
                    recipe=recipe,
                    amount=ingredient['amount'],
                )
                for ingredient in ingredients
            ]
        )

    def create(self, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        recipe = Recipe.objects.create(**validated_data)
        recipe.tags.set(tags_data)
        self.create_ingredients(ingredients_data, recipe)
        return recipe

    def update(self, instance, validated_data):
        ingredients_data = validated_data.pop('ingredients', [])
        tags_data = validated_data.pop('tags', [])
        instance.tags.set(tags_data)
        instance.ingredients.clear()
        self.create_ingredients(ingredients_data, instance)
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        return RecipeDetailSerializer(instance, context=self.context).data


class SubscriptionSerializer(serializers.ModelSerializer):

    class Meta:
        model = Subscription
        fields = ['user', 'author']

    def validate(self, attrs):
        author = attrs.get('author')
        user = attrs.get('user')

        if user == author:
            raise serializers.ValidationError(
                'Нельзя подписаться на самого себя'
            )

        if Subscription.objects.filter(user=user, author=author).exists():
            raise serializers.ValidationError(
                'Вы уже подписаны на этого автора'
            )
        return attrs


class UserListSerializer(serializers.ModelSerializer):
    is_subscribed = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'email',
            'id',
            'username',
            'first_name',
            'last_name',
            'is_subscribed',
            'avatar',
        ]

    def get_is_subscribed(self, obj):
        user = self.context['request'].user
        if user.is_authenticated:
            return Subscription.objects.filter(user=user, author=obj).exists()
        return False


class SubscriptionDetailSerializer(UserListSerializer):
    recipes = serializers.SerializerMethodField(read_only=True)
    recipes_count = serializers.IntegerField(read_only=True)

    class Meta(UserListSerializer.Meta):
        fields = UserListSerializer.Meta.fields + [
            'recipes_count',
            'recipes',
        ]

    def get_recipes(self, obj):
        """Возвращает ограниченный список рецептов автора."""
        limit = self.context['request'].query_params.get('recipes_limit', None)
        recipes = obj.recipe_author.all()
        if limit and limit.isdigit():
            limit = int(limit)
            recipes = recipes[:limit]

        return SimpleRecipeSerializer(
            recipes, many=True, context=self.context
        ).data


class FavoriteRecipeSerializer(serializers.ModelSerializer):
    """Сериализатор для избранного."""

    class Meta:
        model = FavoriteRecipe
        fields = ['recipe', 'user']

    def validate(self, attrs):
        recipe = attrs.get('recipe')
        user = attrs.get('user')
        if FavoriteRecipe.objects.filter(user=user, recipe=recipe).exists():
            raise serializers.ValidationError('Рецепт уже в избранном')
        return attrs

    def to_representation(self, instance):
        return SimpleRecipeSerializer(
            instance.recipe, context=self.context
        ).data


class ShoppingListSerializer(serializers.ModelSerializer):
    """Сериализатор для корзины покупок."""

    class Meta:
        model = ShoppingList
        fields = ['recipe', 'user']

        def validate(self, attrs):
            recipe = attrs.get('recipe')
            user = attrs.get('user')
            if ShoppingList.objects.filter(user=user, recipe=recipe).exists():
                return serializers.ValidationError(
                    'Рецепт уже в списке покупок'
                )
            return attrs

    def to_representation(self, instance):
        return SimpleRecipeSerializer(
            instance.recipe, context=self.context
        ).data
