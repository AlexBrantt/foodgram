from django.contrib.auth.models import AbstractUser
from django.db import models

from user.validators import UsernameValidator
from utils.constants import EMAIL_LENGTH


class User(AbstractUser):
    email = models.EmailField(unique=True, max_length=EMAIL_LENGTH)
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        default='avatars/default.png',
    )
    username = models.CharField(
        max_length=150,
        unique=True,
        help_text=(
            'Required. 150 characters or fewer.'
            ' Letters, digits and @/./+/-/_ only.'
        ),
        validators=[UsernameValidator],
        error_messages={
            'unique': ('A user with that username already exists.'),
        },
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.get_full_name()
