from django.contrib.auth.models import AbstractUser
from django.db import models

from utils.constants import EMAIL_LENGTH, FIRST_LAST_NAME_LENGTH


class User(AbstractUser):
    email = models.EmailField(
        unique=True,
        max_length=EMAIL_LENGTH,
        verbose_name='e-mail',
    )
    avatar = models.ImageField(
        upload_to='avatars/',
        blank=True,
        null=True,
        default='avatars/default.png',
        verbose_name='Аватарка',
    )
    first_name = models.CharField(
        max_length=FIRST_LAST_NAME_LENGTH,
        blank=False,
        null=False,
        verbose_name='Имя',
    )
    last_name = models.CharField(
        max_length=FIRST_LAST_NAME_LENGTH,
        blank=False,
        null=False,
        verbose_name='Фамилия',
    )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name']

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def __str__(self):
        return self.get_full_name()
