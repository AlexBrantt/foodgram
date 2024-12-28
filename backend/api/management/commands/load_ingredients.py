import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = "Загрузить ингредиенты из CSV файла"

    def handle(self, *args, **kwargs):
        file_path = Path(__file__).resolve().parent / 'ingredients.csv'

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    name, measurement_unit = row
                    Ingredient.objects.get_or_create(
                        name=name.strip(),
                        measurement_unit=measurement_unit.strip(),
                    )
            self.stdout.write(
                self.style.SUCCESS("Ингредиенты успешно загружены!")
            )
        except FileNotFoundError:
            self.stdout.write(self.style.ERROR(f"Файл {file_path} не найден."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Ошибка: {e}"))
