from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from rest_framework.routers import DefaultRouter
from user.views import CustomUserViewSet, ChangePasswordView

router = DefaultRouter()
router.register('users', CustomUserViewSet, basename='user')

urlpatterns = [
    path('admin/', admin.site.urls),

    path('api/', include('api.urls')),

    path('api/users/me/avatar/',
         CustomUserViewSet.as_view({'put': 'avatar', 'delete': 'avatar'}),
         name='user-avatar'),
    path('api/users/set_password/', ChangePasswordView.as_view(),
         name='set_password'),
    path('api/', include(router.urls)),

    path('api/auth/', include('djoser.urls.authtoken')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
