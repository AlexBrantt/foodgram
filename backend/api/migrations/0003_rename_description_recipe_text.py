# Generated by Django 4.2.16 on 2024-11-28 02:46

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0002_subscription_shoppinglist_favoriterecipe'),
    ]

    operations = [
        migrations.RenameField(
            model_name='recipe',
            old_name='description',
            new_name='text',
        ),
    ]
