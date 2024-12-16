# from django.contrib.auth import get_user_model
# from rest_framework import serializers

# from api.models import Subscription

# User = get_user_model()


# class UserRegistrationSerializer(serializers.ModelSerializer):

#     class Meta:
#         model = User
#         fields = (
#             'id',
#             'username',
#             'email',
#             'password',
#             'first_name',
#             'last_name',
#         )

#     def create(self, validated_data):
#         user = User(**validated_data)
#         user.set_password(validated_data['password'])
#         user.save()
#         return user


# class UserListSerializer(serializers.ModelSerializer):
#     is_subscribed = serializers.SerializerMethodField()

#     class Meta:
#         model = User
#         fields = [
#             'email',
#             'id',
#             'username',
#             'first_name',
#             'last_name',
#             'is_subscribed',
#             'avatar',
#         ]

#     def get_is_subscribed(self, obj):
#         user = self.context['request'].user
#         if user.is_authenticated:
#             return Subscription.objects.filter(user=user, author=obj).exists()
#         return False
