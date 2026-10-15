from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    AdminUserListView,
    CommentViewSet,
    LoginView,
    LogoutView,
    MeView,
    RecipeBookAPIRootView,
    RecipeViewSet,
    RegisterView,
)


class RecipeBookRouter(DefaultRouter):
    APIRootView = RecipeBookAPIRootView


router = RecipeBookRouter()
router.register('recipes', RecipeViewSet, basename='recipe')
router.register('comments', CommentViewSet, basename='comment')

urlpatterns = [
    # Auth
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/me/', MeView.as_view(), name='me'),

    # Admin
    path('admin/users/', AdminUserListView.as_view(), name='admin-users'),

    # Nested comments under a recipe
    path(
        'recipes/<int:recipe_pk>/comments/',
        CommentViewSet.as_view({'get': 'list', 'post': 'create'}),
        name='recipe-comments',
    ),

    path('', include(router.urls)),
]
