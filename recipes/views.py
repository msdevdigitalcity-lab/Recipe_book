from django.contrib.auth import get_user_model
from django.shortcuts import render
from rest_framework import generics, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.routers import APIRootView
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import Comment, Like, Recipe
from .permissions import IsAdminRole, IsOwnerOrAdminOrReadOnly
from .serializers import (
    CommentCreateSerializer,
    CommentSerializer,
    EmptySerializer,
    LikeSerializer,
    RegisterSerializer,
    RecipeListSerializer,
    RecipeSerializer,
    UserSerializer,
)

User = get_user_model()


class RecipeBookAPIRootView(APIRootView):
    """API index with extra links for likes, comments, and the tips page."""

    def get(self, request, *args, **kwargs):
        response = super().get(request, *args, **kwargs)
        response.data['tips'] = request.build_absolute_uri('/tips/')
        response.data['how_to_like'] = request.build_absolute_uri('/api/recipes/1/like/')
        response.data['how_to_comment'] = request.build_absolute_uri('/api/recipes/1/comment/')
        response.data['how_to_see_likes'] = request.build_absolute_uri('/api/recipes/1/likes/')
        response.data['how_to_see_comments'] = request.build_absolute_uri('/api/recipes/1/comments/')
        return response


def tips_page(request):
    recipes = Recipe.objects.select_related('author').prefetch_related(
        'likes__user',
        'comments__author',
    )
    return render(request, 'recipes/tips.html', {'recipes': recipes})


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]


class LoginView(TokenObtainPairView):
    permission_classes = [AllowAny]


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get('refresh')
        if not refresh_token:
            return Response(
                {'detail': 'Refresh token is required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            return Response(
                {'detail': 'Invalid or expired refresh token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({'detail': 'Successfully logged out.'}, status=status.HTTP_200_OK)


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


class RecipeViewSet(viewsets.ModelViewSet):
    queryset = Recipe.objects.select_related('author').prefetch_related(
        'likes__user',
        'comments__author',
    )
    permission_classes = [IsOwnerOrAdminOrReadOnly]

    def get_permissions(self):
        if self.action in ('like', 'unlike', 'comment'):
            if self.request.method == 'GET':
                return [AllowAny()]
            return [IsAuthenticated()]
        if self.action == 'create':
            return [IsAuthenticated()]
        if self.action == 'likes':
            return [AllowAny()]
        if self.action in ('update', 'partial_update', 'destroy'):
            return [IsAuthenticated(), IsOwnerOrAdminOrReadOnly()]
        return [AllowAny()]

    def get_serializer_class(self):
        if self.action in ('like', 'unlike'):
            return EmptySerializer
        if self.action == 'comment':
            return CommentCreateSerializer
        if self.action == 'list':
            return RecipeListSerializer
        return RecipeSerializer

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    @action(detail=True, methods=['get'], permission_classes=[AllowAny], url_path='likes')
    def likes(self, request, pk=None):
        recipe = self.get_object()
        likes = recipe.likes.select_related('user')
        return Response(
            {
                'recipe_id': recipe.id,
                'recipe': recipe.title,
                'likes_count': likes.count(),
                'liked_by': [like.user.username for like in likes],
                'likes': LikeSerializer(likes, many=True).data,
            }
        )

    @action(detail=True, methods=['get', 'post'], url_path='like')
    def like(self, request, pk=None):
        recipe = self.get_object()
        likes_qs = Like.objects.filter(recipe=recipe)
        payload = {
            'recipe_id': recipe.id,
            'recipe': recipe.title,
            'likes_count': likes_qs.count(),
            'liked_by': list(likes_qs.values_list('user__username', flat=True)),
            'is_liked': (
                request.user.is_authenticated
                and likes_qs.filter(user=request.user).exists()
            ),
        }
        if request.method == 'GET':
            payload['detail'] = (
                'Press POST to like this recipe by id. '
                'This page does not create a recipe.'
            )
            return Response(payload)

        like, created = Like.objects.get_or_create(recipe=recipe, user=request.user)
        payload['likes_count'] = Like.objects.filter(recipe=recipe).count()
        payload['liked_by'] = list(
            Like.objects.filter(recipe=recipe).values_list('user__username', flat=True)
        )
        payload['is_liked'] = True
        if not created:
            payload['detail'] = 'You already liked this recipe.'
            return Response(payload, status=status.HTTP_200_OK)
        payload['detail'] = 'Recipe liked.'
        return Response(payload, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get', 'post'], url_path='comment')
    def comment(self, request, pk=None):
        recipe = self.get_object()
        comments = recipe.comments.select_related('author')
        if request.method == 'GET':
            return Response(
                {
                    'recipe_id': recipe.id,
                    'recipe': recipe.title,
                    'detail': 'Enter text and press POST to comment on this recipe by id.',
                    'comments': CommentSerializer(comments, many=True).data,
                }
            )

        serializer = CommentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        comment = Comment.objects.create(
            recipe=recipe,
            author=request.user,
            text=serializer.validated_data['text'],
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'], url_path='unlike')
    def unlike(self, request, pk=None):
        recipe = self.get_object()
        deleted, _ = Like.objects.filter(recipe=recipe, user=request.user).delete()
        if not deleted:
            return Response(
                {'detail': 'You have not liked this recipe.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {
                'detail': 'Like removed.',
                'likes_count': Like.objects.filter(recipe=recipe).count(),
            },
            status=status.HTTP_200_OK,
        )


class CommentViewSet(viewsets.ModelViewSet):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrAdminOrReadOnly]

    def get_queryset(self):
        queryset = Comment.objects.select_related('author', 'recipe')
        recipe_id = self.kwargs.get('recipe_pk') or self.request.query_params.get('recipe')
        if recipe_id:
            queryset = queryset.filter(recipe_id=recipe_id)
        return queryset

    def get_permissions(self):
        if self.action in ('list', 'retrieve'):
            return [AllowAny()]
        if self.action == 'create':
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsOwnerOrAdminOrReadOnly()]

    def perform_create(self, serializer):
        recipe_id = self.kwargs.get('recipe_pk') or self.request.data.get('recipe')
        try:
            recipe = Recipe.objects.get(pk=recipe_id)
        except (Recipe.DoesNotExist, TypeError, ValueError):
            raise ValidationError({'recipe': 'Valid recipe id is required.'})
        serializer.save(author=self.request.user, recipe=recipe)


class AdminUserListView(generics.ListAPIView):
    """Admin-only: list all users."""

    queryset = User.objects.all().order_by('id')
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated, IsAdminRole]
