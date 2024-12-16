from rest_framework.pagination import PageNumberPagination

from utils.constants import RECIPE_PER_PAGE


class CustomPageNumberPagination(PageNumberPagination):
    page_size = RECIPE_PER_PAGE
    page_size_query_param = 'limit'
