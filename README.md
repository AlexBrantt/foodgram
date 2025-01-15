## Для ревью

- ip: 89.169.161.212
- URL: brantfood.zapto.org
- Email: a@ya.ru
- Pass: 111111


## Проект Foodgram
Соцсеть для рецептов, здесь можно:
Делиться рецептами, добавлять рецепты в избранное, составлять список покупок для желаемых рецптов,
подписываться на авторов любимых рецептов и много чего еще!

## Установка и запуск:

1. Скопируйте проект на свой сервер
```git clone git@github.com:AlexBrantt/foodgram.git```

2. Создать файл .env с таким наполнением:
  - SECRET_KEY=<Ключ проекта Django>
  - POSTGRES_USER=<пользователь бд>
  - POSTGRES_PASSWORD=<пароль бд>
  - POSTGRES_DB=django
  - DB_HOST=db
  - DB_PORT=5432
  - DEBUG=False
  - ALLOWED_HOSTS=<ваш url, ip>

3. Соберите и запустите контейнеры на сервере
```
sudo docker compose -f docker-compose.yml up -d
```

5. Соберите статику и примените миграции командами
```
sudo docker compose exec backend python manage.py collectstatic
sudo docker compose exec backend python manage.py migrate
```

5. Загрузите данные ингредентов в бд командой
```
sudo docker compose exec backend python manage.py load_ingredients
```
