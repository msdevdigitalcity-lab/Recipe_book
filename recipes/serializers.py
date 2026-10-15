from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Comment, Like, Recipe

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'role', 'first_name', 'last_name')
        read_only_fields = ('id', 'role')


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, label='Confirm password')

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'password', 'password2', 'first_name', 'last_name')
        read_only_fields = ('id',)

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({'password': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password2')
        password = validated_data.pop('password')
        user = User(**validated_data, role=User.Role.USER)
        user.set_password(password)
        user.save()
        return user


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    author_id = serializers.IntegerField(source='author.id', read_only=True)

    class Meta:
        model = Comment
        fields = (
            'id',
            'recipe',
            'author',
            'author_id',
            'text',
            'created_at',
            'updated_at',
        )
        read_only_fields = ('id', 'author', 'author_id', 'recipe', 'created_at', 'updated_at')


class RecipeSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    liked_by = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    likes_url = serializers.SerializerMethodField()
    comments_url = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'title',
            'description',
            'ingredients',
            'instructions',
            'cooking_time',
            'likes_count',
            'comments_count',
            'is_liked',
            'liked_by',
            'likes_url',
            'comments_url',
            'comments',
            'created_at',
            'updated_at',
        )
        read_only_fields = (
            'id',
            'author',
            'likes_count',
            'comments_count',
            'is_liked',
            'liked_by',
            'likes_url',
            'comments_url',
            'comments',
            'created_at',
            'updated_at',
        )

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_liked_by(self, obj):
        return [like.user.username for like in obj.likes.all()]

    def get_likes_url(self, obj):
        request = self.context.get('request')
        path = f'/api/recipes/{obj.pk}/likes/'
        return request.build_absolute_uri(path) if request else path

    def get_comments_url(self, obj):
        request = self.context.get('request')
        path = f'/api/recipes/{obj.pk}/comments/'
        return request.build_absolute_uri(path) if request else path


class RecipeListSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)
    likes_count = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    likes_url = serializers.SerializerMethodField()
    comments_url = serializers.SerializerMethodField()

    class Meta:
        model = Recipe
        fields = (
            'id',
            'author',
            'title',
            'description',
            'cooking_time',
            'likes_count',
            'comments_count',
            'is_liked',
            'likes_url',
            'comments_url',
            'created_at',
        )

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_comments_count(self, obj):
        return obj.comments.count()

    def get_is_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False

    def get_likes_url(self, obj):
        request = self.context.get('request')
        path = f'/api/recipes/{obj.pk}/likes/'
        return request.build_absolute_uri(path) if request else path

    def get_comments_url(self, obj):
        request = self.context.get('request')
        path = f'/api/recipes/{obj.pk}/comments/'
        return request.build_absolute_uri(path) if request else path


class LikeSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ('id', 'recipe', 'user', 'created_at')
        read_only_fields = ('id', 'recipe', 'user', 'created_at')


class EmptySerializer(serializers.Serializer):
    """No fields — used so like/unlike pages do not show a recipe form."""


class CommentCreateSerializer(serializers.Serializer):
    text = serializers.CharField()
