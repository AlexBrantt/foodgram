from rest_framework.pagination import PageNumberPagination

from utils.constants import RECIPE_PER_PAGE


class CustomPageNumberPagination(PageNumberPagination):
    page_size = RECIPE_PER_PAGE
    page_size_query_param = 'limit'


# class SubscriptionPagination(PageNumberPagination):
#     def get_page_size(self, request):
#         try:
#             return int(request.query_params.get('limit', self.page_size))
#         except (TypeError, ValueError):
#             return self.page_size
